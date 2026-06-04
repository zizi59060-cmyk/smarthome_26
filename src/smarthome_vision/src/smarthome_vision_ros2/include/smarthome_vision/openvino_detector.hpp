#pragma once

#include <openvino/openvino.hpp>
#include <opencv2/core.hpp>

#include <string>
#include <vector>

#include "smarthome_vision/types.hpp"

namespace smarthome_vision
{

class OpenVINODetector
{
public:
  OpenVINODetector(
    const std::string & model_path,
    int input_width,
    int input_height,
    float conf_thres,
    float score_thres,
    bool output_keypoints,
    const std::string & openvino_device);

  std::vector<RawPrediction> infer(const cv::Mat & image);

private:
  void preprocess(
    const cv::Mat & image,
    std::vector<float> & input_tensor,
    float & scale_x,
    float & scale_y) const;

  std::vector<RawPrediction> decode(
    const float * output,
    int num_preds,
    int row_stride,
    float scale_x,
    float scale_y,
    int image_w,
    int image_h) const;

private:
  std::string model_path_;
  std::string openvino_device_ = "CPU";
  int input_width_ = 640;
  int input_height_ = 640;
  float conf_thres_ = 0.25f;
  float score_thres_ = 0.25f;
  bool output_keypoints_ = false;

  ov::Core core_;
  ov::CompiledModel compiled_model_;
  ov::InferRequest infer_request_;
  ov::Shape input_shape_;
  ov::Shape output_shape_;

  size_t input_numel_ = 0;
  std::vector<float> input_buffer_;
};

}  // namespace smarthome_vision
