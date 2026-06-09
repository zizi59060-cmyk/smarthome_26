#pragma once

#include <memory>
#include <opencv2/core.hpp>
#include <string>
#include <vector>

#include "smarthome_vision/trt_detector.hpp"
#include "smarthome_vision/types.hpp"

namespace smarthome_vision
{

class Detector
{
public:
  Detector(
    const std::string & keypoint_engine_path,
    int input_width,
    int input_height,
    float conf_thres,
    float score_thres,
    bool use_cuda_preprocess);

  std::vector<Detection> infer(const cv::Mat & image);

private:
  static std::array<cv::Point2f, 4> reorder_corners(
    const std::array<cv::Point2f, 4> & pts);

  static bool keypoints_valid(
    const std::array<cv::Point2f, 4> & pts,
    const cv::Rect2f & box,
    int img_w,
    int img_h);

private:
  bool use_cuda_preprocess_ = true;
  std::unique_ptr<TRTDetector> keypoint_detector_;
};

}  // namespace smarthome_vision