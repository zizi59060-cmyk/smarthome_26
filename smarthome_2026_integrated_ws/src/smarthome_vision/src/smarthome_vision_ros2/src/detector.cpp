#include "smarthome_vision/detector.hpp"

#include <opencv2/imgproc.hpp>

#include <cmath>
#include <vector>

namespace smarthome_vision
{

Detector::Detector(
  const std::string & keypoint_engine_path,
  int input_width,
  int input_height,
  float conf_thres,
  float score_thres,
  bool use_cuda_preprocess)
: use_cuda_preprocess_(use_cuda_preprocess)
{
  keypoint_detector_ = std::make_unique<TRTDetector>(
    keypoint_engine_path,
    input_width,
    input_height,
    conf_thres,
    score_thres,
    true,
    use_cuda_preprocess_);
}

// 关键点语义顺序固定：TL, TR, BR, BL
std::array<cv::Point2f, 4> Detector::reorder_corners(
  const std::array<cv::Point2f, 4> & pts)
{
  return pts;
}

bool Detector::keypoints_valid(
  const std::array<cv::Point2f, 4> & pts,
  const cv::Rect2f & box,
  int img_w,
  int img_h)
{
  for (const auto & p : pts) {
    if (p.x < 0.0f || p.y < 0.0f ||
        p.x >= static_cast<float>(img_w) ||
        p.y >= static_cast<float>(img_h))
    {
      return false;
    }
  }

  int outside_count = 0;
  for (const auto & p : pts) {
    if (!box.contains(p)) {
      outside_count++;
    }
  }

  if (outside_count > 1) {
    return false;
  }

  std::vector<cv::Point2f> poly = {pts[0], pts[1], pts[2], pts[3]};
  const float area = std::fabs(static_cast<float>(cv::contourArea(poly)));
  if (area < 25.0f) {
    return false;
  }

  return true;
}

std::vector<Detection> Detector::infer(const cv::Mat & image)
{
  std::vector<Detection> out;
  if (!keypoint_detector_) {
    return out;
  }

  const std::vector<RawPrediction> preds = keypoint_detector_->infer(image);

  for (const auto & pred : preds) {
    if (!pred.has_keypoints) {
      continue;
    }

    if (!keypoints_valid(pred.keypoints, pred.bbox, image.cols, image.rows)) {
      continue;
    }

    Detection det;
    det.class_id = pred.class_id;
    det.score = pred.score;
    det.bbox = pred.bbox;
    det.has_bbox = true;
    det.keypoints = pred.keypoints;
    det.has_keypoints = true;
    det.corners = reorder_corners(pred.keypoints);
    det.corner_source = CornerSource::KEYPOINT;

    out.push_back(det);
  }

  return out;
}

}  // namespace smarthome_vision