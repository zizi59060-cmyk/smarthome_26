#include "smarthome_vision/openvino_detector.hpp"

#include <opencv2/imgproc.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <memory>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace smarthome_vision
{

namespace
{

inline size_t shapeSize(const ov::Shape & shape)
{
  return std::accumulate(
    shape.begin(), shape.end(), static_cast<size_t>(1),
    [](size_t acc, size_t dim) {
      return acc * dim;
    });
}

inline float clampf(float v, float lo, float hi)
{
  return std::max(lo, std::min(v, hi));
}

inline float iouRect(const cv::Rect2f & a, const cv::Rect2f & b)
{
  const float xx1 = std::max(a.x, b.x);
  const float yy1 = std::max(a.y, b.y);
  const float xx2 = std::min(a.x + a.width, b.x + b.width);
  const float yy2 = std::min(a.y + a.height, b.y + b.height);

  const float w = std::max(0.0f, xx2 - xx1);
  const float h = std::max(0.0f, yy2 - yy1);
  const float inter = w * h;
  const float uni = a.area() + b.area() - inter;

  if (uni <= 1e-6f) {
    return 0.0f;
  }
  return inter / uni;
}

std::vector<RawPrediction> applyNms(
  const std::vector<RawPrediction> & input,
  float iou_threshold)
{
  if (input.empty()) {
    return {};
  }

  std::vector<int> order(input.size());
  for (size_t i = 0; i < input.size(); ++i) {
    order[i] = static_cast<int>(i);
  }

  std::sort(order.begin(), order.end(),
    [&](int a, int b) {
      return input[a].score > input[b].score;
    });

  std::vector<RawPrediction> output;
  std::vector<bool> removed(input.size(), false);

  for (size_t oi = 0; oi < order.size(); ++oi) {
    const int i = order[oi];
    if (removed[i]) {
      continue;
    }

    output.push_back(input[i]);

    for (size_t oj = oi + 1; oj < order.size(); ++oj) {
      const int j = order[oj];
      if (removed[j]) {
        continue;
      }

      if (input[i].class_id != input[j].class_id) {
        continue;
      }

      if (iouRect(input[i].bbox, input[j].bbox) > iou_threshold) {
        removed[j] = true;
      }
    }
  }

  return output;
}

}  // namespace

OpenVINODetector::OpenVINODetector(
  const std::string & model_path,
  int input_width,
  int input_height,
  float conf_thres,
  float score_thres,
  bool output_keypoints,
  const std::string & openvino_device)
: model_path_(model_path),
  openvino_device_(openvino_device.empty() ? "CPU" : openvino_device),
  input_width_(input_width),
  input_height_(input_height),
  conf_thres_(conf_thres),
  score_thres_(score_thres),
  output_keypoints_(output_keypoints)
{
  if (model_path_.empty()) {
    throw std::runtime_error("OpenVINO model path is empty");
  }
  if (input_width_ <= 0 || input_height_ <= 0) {
    throw std::runtime_error("invalid input size");
  }

  std::shared_ptr<ov::Model> model = core_.read_model(model_path_);
  if (model->inputs().size() != 1) {
    throw std::runtime_error("OpenVINO detector expects exactly one model input");
  }
  if (model->outputs().size() != 1) {
    throw std::runtime_error("OpenVINO detector expects exactly one model output");
  }

  const auto input = model->input();
  const ov::PartialShape requested_shape{1, 3, input_height_, input_width_};
  if (input.get_partial_shape().is_dynamic() || input.get_shape() != requested_shape.to_shape()) {
    model->reshape({{input.get_any_name(), requested_shape}});
  }

  compiled_model_ = core_.compile_model(model, openvino_device_);
  input_shape_ = compiled_model_.input().get_shape();
  const ov::Shape expected_input_shape{
    1,
    3,
    static_cast<size_t>(input_height_),
    static_cast<size_t>(input_width_)};
  if (input_shape_ != expected_input_shape) {
    throw std::runtime_error("OpenVINO detector expects NCHW input shape [1, 3, H, W]");
  }

  const auto output_partial_shape = compiled_model_.output().get_partial_shape();
  if (output_partial_shape.is_static()) {
    output_shape_ = output_partial_shape.to_shape();
  }

  if (compiled_model_.input().get_element_type() != ov::element::f32) {
    throw std::runtime_error("OpenVINO detector input tensor must be FP32");
  }
  if (compiled_model_.output().get_element_type() != ov::element::f32) {
    throw std::runtime_error("OpenVINO detector output tensor must be FP32");
  }

  input_numel_ = shapeSize(input_shape_);
  input_buffer_.resize(input_numel_);
  infer_request_ = compiled_model_.create_infer_request();

  std::cout << "\n========== OpenVINO model loaded ==========\n";
  std::cout << "Model Path: " << model_path_ << "\n";
  std::cout << "Device: " << openvino_device_ << "\n";
  std::cout << "Output Shape: ";
  if (output_shape_.empty()) {
    std::cout << output_partial_shape;
  } else {
    std::cout << "[ ";
    for (size_t i = 0; i < output_shape_.size(); ++i) {
      std::cout << output_shape_[i] << (i + 1 == output_shape_.size() ? "" : ", ");
    }
    std::cout << " ]";
  }
  std::cout << "\n==========================================\n\n";
}

void OpenVINODetector::preprocess(
  const cv::Mat & image,
  std::vector<float> & input_tensor,
  float & scale_x,
  float & scale_y) const
{
  scale_x = static_cast<float>(image.cols) / static_cast<float>(input_width_);
  scale_y = static_cast<float>(image.rows) / static_cast<float>(input_height_);

  cv::Mat resized, rgb, rgb_float;
  cv::resize(image, resized, cv::Size(input_width_, input_height_));
  cv::cvtColor(resized, rgb, cv::COLOR_BGR2RGB);
  rgb.convertTo(rgb_float, CV_32F, 1.0 / 255.0);

  input_tensor.resize(input_numel_);
  const int hw = input_width_ * input_height_;

  std::vector<cv::Mat> chw(3);
  for (int c = 0; c < 3; ++c) {
    chw[c] = cv::Mat(input_height_, input_width_, CV_32F, input_tensor.data() + c * hw);
  }
  cv::split(rgb_float, chw);
}

std::vector<RawPrediction> OpenVINODetector::infer(const cv::Mat & image)
{
  if (image.empty()) {
    return {};
  }

  float scale_x = 1.0f;
  float scale_y = 1.0f;
  preprocess(image, input_buffer_, scale_x, scale_y);

  ov::Tensor input_tensor(ov::element::f32, input_shape_, input_buffer_.data());
  infer_request_.set_input_tensor(input_tensor);
  infer_request_.infer();

  const ov::Tensor output_tensor = infer_request_.get_output_tensor();
  const float * output = output_tensor.data<const float>();
  const ov::Shape current_output_shape = output_tensor.get_shape();
  const size_t current_output_numel = shapeSize(current_output_shape);

  int num_preds = 0;
  int stride = 0;

  if (current_output_shape.size() == 3) {
    num_preds = static_cast<int>(current_output_shape[1]);
    stride = static_cast<int>(current_output_shape[2]);
  } else if (current_output_shape.size() == 2) {
    num_preds = static_cast<int>(current_output_shape[0]);
    stride = static_cast<int>(current_output_shape[1]);
  } else {
    stride = output_keypoints_ ? 18 : 6;
    num_preds = static_cast<int>(current_output_numel / static_cast<size_t>(stride));
  }

  if (stride <= 0 || num_preds <= 0) {
    return {};
  }

  auto decoded = decode(
    output,
    num_preds,
    stride,
    scale_x,
    scale_y,
    image.cols,
    image.rows);

  return applyNms(decoded, 0.45f);
}

std::vector<RawPrediction> OpenVINODetector::decode(
  const float * output,
  int num_preds,
  int row_stride,
  float scale_x,
  float scale_y,
  int image_w,
  int image_h) const
{
  std::vector<RawPrediction> results;
  if (!output || num_preds <= 0) {
    return results;
  }

  const int expected_stride = output_keypoints_ ? 18 : 6;
  if (row_stride < expected_stride) {
    throw std::runtime_error("OpenVINO detector output stride is smaller than expected");
  }

  for (int i = 0; i < num_preds; ++i) {
    const float * row = output + i * row_stride;
    const float score = row[4];
    if (score < score_thres_) {
      continue;
    }

    float x1 = row[0] * scale_x;
    float y1 = row[1] * scale_y;
    float x2 = row[2] * scale_x;
    float y2 = row[3] * scale_y;

    x1 = clampf(x1, 0.0f, static_cast<float>(image_w - 1));
    y1 = clampf(y1, 0.0f, static_cast<float>(image_h - 1));
    x2 = clampf(x2, 0.0f, static_cast<float>(image_w - 1));
    y2 = clampf(y2, 0.0f, static_cast<float>(image_h - 1));

    if (x2 <= x1 || y2 <= y1) {
      continue;
    }

    RawPrediction pred;
    pred.score = score;
    pred.class_id = static_cast<int>(std::lround(row[5]));
    pred.bbox = cv::Rect2f(x1, y1, x2 - x1, y2 - y1);

    if (output_keypoints_) {
      pred.has_keypoints = true;

      constexpr int kNumKpts = 4;
      constexpr int kKptBase = 6;
      constexpr int kKptStride = 3;

      std::array<float, kNumKpts> kpt_vis{};

      for (int k = 0; k < kNumKpts; ++k) {
        const int base = kKptBase + k * kKptStride;
        const float kx = row[base + 0] * scale_x;
        const float ky = row[base + 1] * scale_y;
        const float kv = row[base + 2];

        pred.keypoints[k] = cv::Point2f(kx, ky);
        kpt_vis[k] = kv;
      }

      int valid_kpt_count = 0;
      for (int k = 0; k < kNumKpts; ++k) {
        if (kpt_vis[k] >= conf_thres_) {
          ++valid_kpt_count;
        }
      }

      if (valid_kpt_count < kNumKpts) {
        continue;
      }
    } else {
      pred.has_keypoints = false;
    }

    results.push_back(pred);
  }

  return results;
}

}  // namespace smarthome_vision
