#pragma once

#include <array>
#include <deque>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "smarthome_vision/types.hpp"

namespace smarthome_vision
{

class TraditionalQrDetector
{
public:
  TraditionalQrDetector();
  ~TraditionalQrDetector();

  std::vector<Detection> infer(const cv::Mat & image, bool show_tuning_windows);
  void closeTuningWindows();

  static std::string className(int class_id);

private:
  struct Params
  {
    int black_tag_mode = 2;
    int threshold = 128;
    int invert = 0;
    int blur = 1;
    int open = 0;
    int close = 1;
    int group_dilate = 3;
    int min_area_x100 = 2;
    int max_area_x1000 = 900;
    int pad_percent = 18;
    int tag_inset_percent = 0;
    int min_tag_fill_percent = 45;
    int cell_on_percent = 35;
    int min_score_percent = 72;
    int min_margin_percent = 8;
    int ratio_tol_percent = 18;
    int allow_rotation = 1;
  };

  struct TemplateVariant
  {
    int class_id = -1;
    std::string label;
    int rotation = 0;
    cv::Mat mask;
    cv::Mat grid;
    double white_ratio = 0.0;
    int components = 0;
  };

  struct Candidate
  {
    cv::Rect bbox;
    std::array<cv::Point2f, 4> corners{};
    cv::Mat mask;
    cv::Mat grid;
    double white_ratio = 0.0;
    int components = 0;
  };

  struct MatchResult
  {
    bool accepted = false;
    int class_id = -1;
    std::string label;
    float score = 0.0f;
    float margin = 0.0f;
    int rotation = 0;
  };

  void ensureTuningWindows();
  void rebuildTemplatesIfNeeded();

  cv::Mat preprocess(const cv::Mat & image) const;
  std::vector<Candidate> findWhitePartCandidates(
    const cv::Mat & mask,
    cv::Mat * grouped_debug) const;
  std::vector<Candidate> findBlackTagCandidates(
    const cv::Mat & mask,
    cv::Mat * grouped_debug) const;
  std::vector<Candidate> findBlackCodeCandidates(
    const cv::Mat & mask,
    cv::Mat * grouped_debug) const;
  std::vector<Candidate> findCandidates(
    const cv::Mat & mask,
    cv::Mat * grouped_debug) const;
  MatchResult matchCandidate(const Candidate & candidate) const;

  cv::Mat maskToGrid(const cv::Mat & mask) const;
  int countComponents(const cv::Mat & mask) const;

  Params params_;
  bool windows_created_ = false;
  int last_black_tag_mode_ = -1;
  int last_cell_on_percent_ = -1;
  int last_allow_rotation_ = -1;
  int last_pad_percent_ = -1;
  std::vector<TemplateVariant> templates_;
};

}  // namespace smarthome_vision
