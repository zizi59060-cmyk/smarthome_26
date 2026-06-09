#include "smarthome_vision/traditional_qr_detector.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

namespace smarthome_vision
{

namespace
{

constexpr int kNormSize = 96;
constexpr int kGridSize = 12;

struct GridTemplate
{
  int class_id;
  const char * label;
  std::array<const char *, kGridSize> rows;
};

const std::array<GridTemplate, 4> & gridTemplates()
{
  static const std::array<GridTemplate, 4> templates = {{
    {
      0,
      "meat",
      {
        "............",
        "............",
        "........##..",
        "..###....#..",
        "..###.......",
        ".........#..",
        "........##..",
        "..##.#####..",
        "..#..#####..",
        ".....####...",
        "............",
        "............",
      },
    },
    {
      1,
      "vegetable",
      {
        "............",
        "............",
        "..###..##...",
        "..#######...",
        "..#######...",
        ".......###..",
        ".......###..",
        "..##.####...",
        "..########..",
        "..#####.##..",
        "............",
        "............",
      },
    },
    {
      2,
      "fruit",
      {
        "............",
        "............",
        "..##........",
        "..#...####..",
        ".....#####..",
        ".....##.##..",
        ".....##.##..",
        "...#######..",
        "..########..",
        "..##.#####..",
        "............",
        "............",
      },
    },
    {
      3,
      "drink",
      {
        "............",
        "............",
        "..###..##...",
        "..########..",
        "..#####.##..",
        "...####.##..",
        "...####.##..",
        "...##...##..",
        "....###..#..",
        ".....##.....",
        "............",
        "............",
      },
    },
  }};

  return templates;
}

int oddKernel(int value)
{
  if (value <= 0) {
    return 0;
  }
  return value * 2 + 1;
}

cv::Mat rotateMask(const cv::Mat & mask, int angle)
{
  cv::Mat rotated;
  if (angle == 0) {
    return mask.clone();
  }
  if (angle == 90) {
    cv::rotate(mask, rotated, cv::ROTATE_90_CLOCKWISE);
  } else if (angle == 180) {
    cv::rotate(mask, rotated, cv::ROTATE_180);
  } else {
    cv::rotate(mask, rotated, cv::ROTATE_90_COUNTERCLOCKWISE);
  }
  return rotated;
}

cv::Mat templateMaskFromGrid(const GridTemplate & tmpl)
{
  cv::Mat small(kGridSize, kGridSize, CV_8UC1, cv::Scalar(0));
  for (int y = 0; y < kGridSize; ++y) {
    const char * row = tmpl.rows[static_cast<size_t>(y)];
    for (int x = 0; x < kGridSize; ++x) {
      if (row[x] == '#') {
        small.at<uchar>(y, x) = 255;
      }
    }
  }

  cv::Mat out;
  cv::resize(small, out, cv::Size(kNormSize, kNormSize), 0.0, 0.0, cv::INTER_NEAREST);
  return out;
}

cv::Rect foregroundBBox(const cv::Mat & mask)
{
  std::vector<cv::Point> points;
  cv::findNonZero(mask, points);
  if (points.empty()) {
    return {};
  }
  return cv::boundingRect(points);
}

cv::Rect squareRectAround(const cv::Rect & bbox, double pad_frac)
{
  if (bbox.empty()) {
    return {};
  }

  const int side = static_cast<int>(
    std::round(std::max(bbox.width, bbox.height) * (1.0 + 2.0 * pad_frac)));
  if (side <= 0) {
    return {};
  }

  const double cx = bbox.x + bbox.width / 2.0;
  const double cy = bbox.y + bbox.height / 2.0;
  const int x0 = static_cast<int>(std::round(cx - side / 2.0));
  const int y0 = static_cast<int>(std::round(cy - side / 2.0));
  return cv::Rect(x0, y0, side, side);
}

cv::Mat cropSquare(const cv::Mat & mask, const cv::Rect & bbox, double pad_frac)
{
  if (bbox.empty()) {
    return {};
  }

  const cv::Rect wanted = squareRectAround(bbox, pad_frac);
  if (wanted.empty()) {
    return {};
  }

  const int side = wanted.width;
  const int x0 = wanted.x;
  const int y0 = wanted.y;
  const cv::Rect dst_rect(0, 0, side, side);
  const cv::Rect src_rect(0, 0, mask.cols, mask.rows);
  const cv::Rect src = wanted & src_rect;
  if (src.empty()) {
    return {};
  }

  cv::Mat square(side, side, CV_8UC1, cv::Scalar(0));
  const cv::Rect dst(src.x - x0, src.y - y0, src.width, src.height);
  if (dst.x < dst_rect.x || dst.y < dst_rect.y ||
      dst.x + dst.width > dst_rect.width ||
      dst.y + dst.height > dst_rect.height)
  {
    return {};
  }

  mask(src).copyTo(square(dst));

  cv::Mat out;
  cv::resize(square, out, cv::Size(kNormSize, kNormSize), 0.0, 0.0, cv::INTER_NEAREST);
  return out;
}

cv::Mat cropResizeRect(const cv::Mat & mask, const cv::Rect & bbox, double inset_frac)
{
  const int inset_x = static_cast<int>(std::round(bbox.width * inset_frac));
  const int inset_y = static_cast<int>(std::round(bbox.height * inset_frac));

  cv::Rect inner(
    bbox.x + inset_x,
    bbox.y + inset_y,
    bbox.width - inset_x * 2,
    bbox.height - inset_y * 2);
  inner &= cv::Rect(0, 0, mask.cols, mask.rows);
  if (inner.empty()) {
    return {};
  }

  cv::Mat out;
  cv::resize(mask(inner), out, cv::Size(kNormSize, kNormSize), 0.0, 0.0, cv::INTER_NEAREST);
  return out;
}

std::array<cv::Point2f, 4> cornersFromRect(const cv::Rect & bbox)
{
  return {
    cv::Point2f(static_cast<float>(bbox.x), static_cast<float>(bbox.y)),
    cv::Point2f(static_cast<float>(bbox.x + bbox.width), static_cast<float>(bbox.y)),
    cv::Point2f(static_cast<float>(bbox.x + bbox.width), static_cast<float>(bbox.y + bbox.height)),
    cv::Point2f(static_cast<float>(bbox.x), static_cast<float>(bbox.y + bbox.height)),
  };
}

std::array<cv::Point2f, 4> orderCorners(const std::array<cv::Point2f, 4> & pts)
{
  std::array<cv::Point2f, 4> ordered{};

  auto sum = [](const cv::Point2f & p) { return p.x + p.y; };
  auto diff = [](const cv::Point2f & p) { return p.x - p.y; };

  ordered[0] = *std::min_element(pts.begin(), pts.end(),
    [&](const cv::Point2f & a, const cv::Point2f & b) { return sum(a) < sum(b); });
  ordered[2] = *std::max_element(pts.begin(), pts.end(),
    [&](const cv::Point2f & a, const cv::Point2f & b) { return sum(a) < sum(b); });
  ordered[1] = *std::max_element(pts.begin(), pts.end(),
    [&](const cv::Point2f & a, const cv::Point2f & b) { return diff(a) < diff(b); });
  ordered[3] = *std::min_element(pts.begin(), pts.end(),
    [&](const cv::Point2f & a, const cv::Point2f & b) { return diff(a) < diff(b); });

  return ordered;
}

std::array<cv::Point2f, 4> cornersFromBlackMask(const cv::Mat & black, const cv::Rect & bbox)
{
  std::vector<cv::Point> local_points;
  cv::findNonZero(black(bbox), local_points);

  if (local_points.size() >= 4) {
    for (auto & p : local_points) {
      p.x += bbox.x;
      p.y += bbox.y;
    }

    const cv::RotatedRect rr = cv::minAreaRect(local_points);
    cv::Point2f pts_raw[4];
    rr.points(pts_raw);
    std::array<cv::Point2f, 4> pts = {pts_raw[0], pts_raw[1], pts_raw[2], pts_raw[3]};
    return orderCorners(pts);
  }

  return {
    cv::Point2f(static_cast<float>(bbox.x), static_cast<float>(bbox.y)),
    cv::Point2f(static_cast<float>(bbox.x + bbox.width), static_cast<float>(bbox.y)),
    cv::Point2f(static_cast<float>(bbox.x + bbox.width), static_cast<float>(bbox.y + bbox.height)),
    cv::Point2f(static_cast<float>(bbox.x), static_cast<float>(bbox.y + bbox.height)),
  };
}

double diceScore(const cv::Mat & a, const cv::Mat & b)
{
  cv::Mat inter;
  cv::bitwise_and(a, b, inter);
  const double inter_count = static_cast<double>(cv::countNonZero(inter));
  const double denom = static_cast<double>(cv::countNonZero(a) + cv::countNonZero(b));
  if (denom <= 0.0) {
    return 0.0;
  }
  return 2.0 * inter_count / denom;
}

double agreementScore(const cv::Mat & a, const cv::Mat & b)
{
  cv::Mat same;
  cv::compare(a, b, same, cv::CMP_EQ);
  return static_cast<double>(cv::countNonZero(same)) /
         static_cast<double>(same.rows * same.cols);
}

double ratioScore(double candidate_ratio, double template_ratio, double tolerance)
{
  return std::max(0.0, 1.0 - std::abs(candidate_ratio - template_ratio) / tolerance);
}

double componentScore(int candidate_count, int template_count)
{
  const int denom = std::max(1, template_count);
  return std::max(0.0, 1.0 - std::abs(candidate_count - template_count) / static_cast<double>(denom));
}

}  // namespace

TraditionalQrDetector::TraditionalQrDetector()
{
  rebuildTemplatesIfNeeded();
}

TraditionalQrDetector::~TraditionalQrDetector()
{
  closeTuningWindows();
}

std::string TraditionalQrDetector::className(int class_id)
{
  switch (class_id) {
    case 0:
      return "meat";
    case 1:
      return "vegetable";
    case 2:
      return "fruit";
    case 3:
      return "drink";
    default:
      return "";
  }
}

void TraditionalQrDetector::ensureTuningWindows()
{
  if (windows_created_) {
    return;
  }

  cv::namedWindow("traditional_qr_params", cv::WINDOW_NORMAL);
  cv::resizeWindow("traditional_qr_params", 460, 680);
  cv::createTrackbar("mode 0=white 1=blacktag 2=code-only", "traditional_qr_params", &params_.black_tag_mode, 2);
  cv::createTrackbar("threshold 0=otsu", "traditional_qr_params", &params_.threshold, 255);
  cv::createTrackbar("invert", "traditional_qr_params", &params_.invert, 1);
  cv::createTrackbar("blur", "traditional_qr_params", &params_.blur, 5);
  cv::createTrackbar("open", "traditional_qr_params", &params_.open, 5);
  cv::createTrackbar("close", "traditional_qr_params", &params_.close, 8);
  cv::createTrackbar("group dilate", "traditional_qr_params", &params_.group_dilate, 20);
  cv::createTrackbar("min area x100", "traditional_qr_params", &params_.min_area_x100, 200);
  cv::createTrackbar("max area x1000", "traditional_qr_params", &params_.max_area_x1000, 3000);
  cv::createTrackbar("pad percent", "traditional_qr_params", &params_.pad_percent, 60);
  cv::createTrackbar("tag inset percent", "traditional_qr_params", &params_.tag_inset_percent, 25);
  cv::createTrackbar("min tag fill percent", "traditional_qr_params", &params_.min_tag_fill_percent, 95);
  cv::createTrackbar("cell on percent", "traditional_qr_params", &params_.cell_on_percent, 80);
  cv::createTrackbar("min score", "traditional_qr_params", &params_.min_score_percent, 100);
  cv::createTrackbar("min margin", "traditional_qr_params", &params_.min_margin_percent, 40);
  cv::createTrackbar("ratio tol percent", "traditional_qr_params", &params_.ratio_tol_percent, 60);
  cv::createTrackbar("allow rotation", "traditional_qr_params", &params_.allow_rotation, 1);

  cv::namedWindow("traditional_qr_mask", cv::WINDOW_NORMAL);
  cv::namedWindow("traditional_qr_grouped", cv::WINDOW_NORMAL);
  windows_created_ = true;
}

void TraditionalQrDetector::closeTuningWindows()
{
  if (!windows_created_) {
    return;
  }
  cv::destroyWindow("traditional_qr_params");
  cv::destroyWindow("traditional_qr_mask");
  cv::destroyWindow("traditional_qr_grouped");
  windows_created_ = false;
}

void TraditionalQrDetector::rebuildTemplatesIfNeeded()
{
  if (last_black_tag_mode_ == params_.black_tag_mode &&
      last_cell_on_percent_ == params_.cell_on_percent &&
      last_allow_rotation_ == params_.allow_rotation &&
      last_pad_percent_ == params_.pad_percent &&
      !templates_.empty())
  {
    return;
  }

  templates_.clear();
  const std::array<int, 4> rotations =
    params_.allow_rotation != 0 ? std::array<int, 4>{0, 90, 180, 270} :
      std::array<int, 4>{0, 0, 0, 0};
  const int rotation_count = params_.allow_rotation != 0 ? 4 : 1;

  for (const auto & tmpl : gridTemplates()) {
    cv::Mat base = templateMaskFromGrid(tmpl);
    if (params_.black_tag_mode != 1) {
      const cv::Rect bbox = foregroundBBox(base);
      base = cropSquare(base, bbox, std::max(0.0, params_.pad_percent / 100.0));
      if (base.empty()) {
        continue;
      }
    }

    for (int i = 0; i < rotation_count; ++i) {
      cv::Mat rotated = rotateMask(base, rotations[static_cast<size_t>(i)]);

      TemplateVariant variant;
      variant.class_id = tmpl.class_id;
      variant.label = tmpl.label;
      variant.rotation = rotations[static_cast<size_t>(i)];
      cv::threshold(rotated, variant.mask, 0, 1, cv::THRESH_BINARY);
      variant.grid = maskToGrid(rotated);
      variant.white_ratio =
        static_cast<double>(cv::countNonZero(variant.mask)) /
        static_cast<double>(variant.mask.rows * variant.mask.cols);
      variant.components = countComponents(rotated);
      templates_.push_back(std::move(variant));
    }
  }

  last_black_tag_mode_ = params_.black_tag_mode;
  last_cell_on_percent_ = params_.cell_on_percent;
  last_allow_rotation_ = params_.allow_rotation;
  last_pad_percent_ = params_.pad_percent;
}

cv::Mat TraditionalQrDetector::preprocess(const cv::Mat & image) const
{
  cv::Mat gray;
  if (image.channels() == 3) {
    cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
  } else {
    gray = image.clone();
  }

  cv::Mat work = gray;
  const int blur_kernel = oddKernel(params_.blur);
  if (blur_kernel > 1) {
    cv::GaussianBlur(work, work, cv::Size(blur_kernel, blur_kernel), 0.0);
  }

  cv::Mat mask;
  if (params_.threshold <= 0) {
    cv::threshold(work, mask, 0.0, 255.0, cv::THRESH_BINARY | cv::THRESH_OTSU);
  } else {
    cv::threshold(work, mask, static_cast<double>(params_.threshold), 255.0, cv::THRESH_BINARY);
  }

  bool invert_mask = params_.invert != 0;
  if (params_.black_tag_mode == 2) {
    invert_mask = !invert_mask;
  }
  if (invert_mask) {
    cv::bitwise_not(mask, mask);
  }

  const int open_kernel = oddKernel(params_.open);
  if (open_kernel > 1) {
    cv::Mat kernel = cv::Mat::ones(open_kernel, open_kernel, CV_8UC1);
    cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel);
  }

  const int close_kernel = oddKernel(params_.close);
  if (close_kernel > 1) {
    cv::Mat kernel = cv::Mat::ones(close_kernel, close_kernel, CV_8UC1);
    cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, kernel);
  }

  return mask;
}

cv::Mat TraditionalQrDetector::maskToGrid(const cv::Mat & mask) const
{
  cv::Mat binary;
  cv::threshold(mask, binary, 0, 1, cv::THRESH_BINARY);

  cv::Mat grid(kGridSize, kGridSize, CV_8UC1, cv::Scalar(0));
  const double cell_on = std::max(0.05, params_.cell_on_percent / 100.0);

  for (int gy = 0; gy < kGridSize; ++gy) {
    const int y0 = static_cast<int>(std::round(gy * binary.rows / static_cast<double>(kGridSize)));
    const int y1 = static_cast<int>(std::round((gy + 1) * binary.rows / static_cast<double>(kGridSize)));
    for (int gx = 0; gx < kGridSize; ++gx) {
      const int x0 = static_cast<int>(std::round(gx * binary.cols / static_cast<double>(kGridSize)));
      const int x1 = static_cast<int>(std::round((gx + 1) * binary.cols / static_cast<double>(kGridSize)));

      const cv::Rect cell(x0, y0, std::max(0, x1 - x0), std::max(0, y1 - y0));
      if (cell.empty()) {
        continue;
      }
      const double ratio =
        static_cast<double>(cv::countNonZero(binary(cell))) /
        static_cast<double>(cell.area());
      if (ratio >= cell_on) {
        grid.at<uchar>(gy, gx) = 1;
      }
    }
  }

  return grid;
}

int TraditionalQrDetector::countComponents(const cv::Mat & mask) const
{
  cv::Mat binary;
  cv::threshold(mask, binary, 0, 1, cv::THRESH_BINARY);

  cv::Mat labels, stats, centroids;
  const int n = cv::connectedComponentsWithStats(binary, labels, stats, centroids, 8);
  const int min_area = std::max(4, static_cast<int>(mask.total() * 0.0015));

  int count = 0;
  for (int i = 1; i < n; ++i) {
    if (stats.at<int>(i, cv::CC_STAT_AREA) >= min_area) {
      ++count;
    }
  }
  return count;
}

std::vector<TraditionalQrDetector::Candidate> TraditionalQrDetector::findBlackTagCandidates(
  const cv::Mat & mask,
  cv::Mat * grouped_debug) const
{
  cv::Mat black_regions;
  cv::bitwise_not(mask, black_regions);

  cv::Mat grouped = black_regions.clone();
  const int group_kernel_size = std::max(1, params_.group_dilate);
  if (group_kernel_size > 1) {
    cv::Mat kernel = cv::Mat::ones(group_kernel_size, group_kernel_size, CV_8UC1);
    cv::morphologyEx(grouped, grouped, cv::MORPH_CLOSE, kernel);
    cv::dilate(grouped, grouped, kernel);
  }

  if (grouped_debug != nullptr) {
    *grouped_debug = grouped.clone();
  }

  std::vector<std::vector<cv::Point>> contours;
  cv::findContours(grouped, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

  std::vector<Candidate> candidates;
  const int min_area = std::max(1, params_.min_area_x100 * 100);
  const int max_area = std::max(min_area, params_.max_area_x1000 * 1000);
  const double inset = std::max(0.0, params_.tag_inset_percent / 100.0);
  const double min_fill = std::max(0.0, params_.min_tag_fill_percent / 100.0);
  const cv::Rect image_rect(0, 0, mask.cols, mask.rows);

  for (const auto & contour : contours) {
    cv::Rect bbox = cv::boundingRect(contour) & image_rect;
    if (bbox.empty()) {
      continue;
    }

    cv::Rect tight = foregroundBBox(black_regions(bbox));
    if (tight.empty()) {
      continue;
    }
    tight.x += bbox.x;
    tight.y += bbox.y;
    tight &= image_rect;

    const int area = tight.area();
    if (area < min_area || area > max_area) {
      continue;
    }
    if (tight.x <= 2 || tight.y <= 2 ||
        tight.x + tight.width >= mask.cols - 2 ||
        tight.y + tight.height >= mask.rows - 2)
    {
      continue;
    }

    const double aspect = tight.width / static_cast<double>(tight.height);
    if (aspect < 0.30 || aspect > 2.30) {
      continue;
    }

    const double fill_ratio =
      static_cast<double>(cv::countNonZero(black_regions(tight))) /
      static_cast<double>(area);
    if (fill_ratio < min_fill || fill_ratio > 0.98) {
      continue;
    }

    cv::Mat normalized = cropResizeRect(mask, tight, inset);
    if (normalized.empty()) {
      continue;
    }

    cv::Mat normalized_binary;
    cv::threshold(normalized, normalized_binary, 0, 1, cv::THRESH_BINARY);
    const double white_ratio =
      static_cast<double>(cv::countNonZero(normalized_binary)) /
      static_cast<double>(normalized_binary.rows * normalized_binary.cols);
    if (white_ratio < 0.03 || white_ratio > 0.75) {
      continue;
    }

    Candidate candidate;
    candidate.bbox = tight;
    candidate.corners = cornersFromBlackMask(black_regions, tight);
    candidate.mask = normalized_binary;
    candidate.grid = maskToGrid(normalized);
    candidate.white_ratio = white_ratio;
    candidate.components = countComponents(normalized);
    candidates.push_back(std::move(candidate));
  }

  std::sort(candidates.begin(), candidates.end(),
    [](const Candidate & a, const Candidate & b) {
      return a.bbox.area() > b.bbox.area();
    });

  return candidates;
}

std::vector<TraditionalQrDetector::Candidate> TraditionalQrDetector::findWhitePartCandidates(
  const cv::Mat & mask,
  cv::Mat * grouped_debug) const
{
  cv::Mat grouped = mask.clone();
  const int group_kernel_size = std::max(1, params_.group_dilate);
  if (group_kernel_size > 1) {
    cv::Mat kernel = cv::Mat::ones(group_kernel_size, group_kernel_size, CV_8UC1);
    cv::dilate(grouped, grouped, kernel);
    cv::morphologyEx(grouped, grouped, cv::MORPH_CLOSE, kernel);
  }

  if (grouped_debug != nullptr) {
    *grouped_debug = grouped.clone();
  }

  std::vector<std::vector<cv::Point>> contours;
  cv::findContours(grouped, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

  std::vector<Candidate> candidates;
  const int min_area = std::max(1, params_.min_area_x100 * 100);
  const int max_area = std::max(min_area, params_.max_area_x1000 * 1000);
  const double pad = std::max(0.0, params_.pad_percent / 100.0);
  const cv::Rect image_rect(0, 0, mask.cols, mask.rows);

  for (const auto & contour : contours) {
    cv::Rect bbox = cv::boundingRect(contour) & image_rect;
    if (bbox.empty()) {
      continue;
    }

    const int area = bbox.area();
    if (area < min_area || area > max_area) {
      continue;
    }

    const double aspect = bbox.width / static_cast<double>(bbox.height);
    if (aspect < 0.55 || aspect > 1.85) {
      continue;
    }

    cv::Rect raw_bbox = foregroundBBox(mask(bbox));
    if (raw_bbox.empty()) {
      continue;
    }
    raw_bbox.x += bbox.x;
    raw_bbox.y += bbox.y;
    raw_bbox &= image_rect;

    cv::Mat normalized = cropSquare(mask, raw_bbox, pad);
    if (normalized.empty()) {
      continue;
    }

    cv::Mat normalized_binary;
    cv::threshold(normalized, normalized_binary, 0, 1, cv::THRESH_BINARY);
    const double white_ratio =
      static_cast<double>(cv::countNonZero(normalized_binary)) /
      static_cast<double>(normalized_binary.rows * normalized_binary.cols);
    if (white_ratio < 0.03 || white_ratio > 0.75) {
      continue;
    }

    Candidate candidate;
    candidate.bbox = squareRectAround(raw_bbox, pad);
    candidate.corners = cornersFromRect(candidate.bbox);
    candidate.mask = normalized_binary;
    candidate.grid = maskToGrid(normalized);
    candidate.white_ratio = white_ratio;
    candidate.components = countComponents(normalized);
    candidates.push_back(std::move(candidate));
  }

  std::sort(candidates.begin(), candidates.end(),
    [](const Candidate & a, const Candidate & b) {
      return a.bbox.area() > b.bbox.area();
    });

  return candidates;
}

std::vector<TraditionalQrDetector::Candidate> TraditionalQrDetector::findBlackCodeCandidates(
  const cv::Mat & mask,
  cv::Mat * grouped_debug) const
{
  cv::Mat foreground = mask.clone();
  const double foreground_ratio =
    static_cast<double>(cv::countNonZero(foreground)) /
    static_cast<double>(foreground.rows * foreground.cols);
  if (foreground_ratio > 0.5) {
    cv::bitwise_not(foreground, foreground);
  }

  cv::Mat grouped = foreground.clone();
  const int group_kernel_size = std::max(3, params_.group_dilate * 10 + 1);
  cv::Mat kernel = cv::Mat::ones(group_kernel_size, group_kernel_size, CV_8UC1);
  cv::morphologyEx(grouped, grouped, cv::MORPH_CLOSE, kernel);
  cv::dilate(grouped, grouped, kernel);

  if (grouped_debug != nullptr) {
    *grouped_debug = grouped.clone();
  }

  std::vector<std::vector<cv::Point>> contours;
  cv::findContours(grouped, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

  const cv::Rect image_rect(0, 0, mask.cols, mask.rows);
  const int min_area = std::max(1, params_.min_area_x100 * 100);
  const int max_area = std::max(min_area, params_.max_area_x1000 * 1000);
  const double pad = std::max(0.0, params_.pad_percent / 100.0);
  std::vector<Candidate> candidates;

  for (const auto & contour : contours) {
    cv::Rect bbox = cv::boundingRect(contour) & image_rect;
    if (bbox.empty()) {
      continue;
    }

    if (bbox.x <= 2 || bbox.y <= 2 ||
        bbox.x + bbox.width >= mask.cols - 2 ||
        bbox.y + bbox.height >= mask.rows - 2)
    {
      continue;
    }

    const int area = bbox.area();
    if (area < min_area || area > max_area) {
      continue;
    }

    const double aspect = bbox.width / static_cast<double>(bbox.height);
    if (aspect < 0.40 || aspect > 2.50) {
      continue;
    }

    cv::Rect raw_bbox = foregroundBBox(foreground(bbox));
    if (raw_bbox.empty()) {
      continue;
    }
    raw_bbox.x += bbox.x;
    raw_bbox.y += bbox.y;
    raw_bbox &= image_rect;

    cv::Mat normalized = cropSquare(foreground, raw_bbox, pad);
    if (normalized.empty()) {
      continue;
    }

    cv::Mat normalized_binary;
    cv::threshold(normalized, normalized_binary, 0, 1, cv::THRESH_BINARY);
    const double white_ratio =
      static_cast<double>(cv::countNonZero(normalized_binary)) /
      static_cast<double>(normalized_binary.rows * normalized_binary.cols);
    if (white_ratio < 0.03 || white_ratio > 0.75) {
      continue;
    }

    Candidate candidate;
    candidate.bbox = squareRectAround(raw_bbox, pad);
    candidate.corners = cornersFromRect(candidate.bbox);
    candidate.mask = normalized_binary;
    candidate.grid = maskToGrid(normalized);
    candidate.white_ratio = white_ratio;
    candidate.components = countComponents(normalized);
    candidates.push_back(std::move(candidate));
  }

  std::sort(candidates.begin(), candidates.end(),
    [](const Candidate & a, const Candidate & b) {
      return a.bbox.area() > b.bbox.area();
    });

  return candidates;
}

std::vector<TraditionalQrDetector::Candidate> TraditionalQrDetector::findCandidates(
  const cv::Mat & mask,
  cv::Mat * grouped_debug) const
{
  if (params_.black_tag_mode == 1) {
    return findBlackTagCandidates(mask, grouped_debug);
  }
  if (params_.black_tag_mode == 2) {
    return findBlackCodeCandidates(mask, grouped_debug);
  }
  return findWhitePartCandidates(mask, grouped_debug);
}

TraditionalQrDetector::MatchResult TraditionalQrDetector::matchCandidate(
  const Candidate & candidate) const
{
  MatchResult result;
  if (templates_.empty()) {
    return result;
  }

  const double ratio_tol = std::max(0.01, params_.ratio_tol_percent / 100.0);
  std::vector<std::pair<double, const TemplateVariant *>> ranked;
  ranked.reserve(templates_.size());

  for (const auto & tmpl : templates_) {
    const double pixel = diceScore(candidate.mask, tmpl.mask);
    const double grid_dice = diceScore(candidate.grid, tmpl.grid);
    const double grid_agree = agreementScore(candidate.grid, tmpl.grid);
    const double grid_score = 0.75 * grid_dice + 0.25 * grid_agree;
    const double density = ratioScore(candidate.white_ratio, tmpl.white_ratio, ratio_tol);
    const double comp = componentScore(candidate.components, tmpl.components);
    const double score = 0.58 * pixel + 0.27 * grid_score + 0.10 * density + 0.05 * comp;
    ranked.push_back({score, &tmpl});
  }

  std::sort(ranked.begin(), ranked.end(),
    [](const auto & a, const auto & b) {
      return a.first > b.first;
    });

  if (ranked.empty()) {
    return result;
  }

  const double best_score = ranked[0].first;
  const double second_score = ranked.size() > 1 ? ranked[1].first : 0.0;
  const double margin = best_score - second_score;
  const double min_score = params_.min_score_percent / 100.0;
  const double min_margin = params_.min_margin_percent / 100.0;

  result.class_id = ranked[0].second->class_id;
  result.label = ranked[0].second->label;
  result.score = static_cast<float>(best_score);
  result.margin = static_cast<float>(margin);
  result.rotation = ranked[0].second->rotation;
  result.accepted = best_score >= min_score && margin >= min_margin;
  return result;
}

std::vector<Detection> TraditionalQrDetector::infer(
  const cv::Mat & image,
  bool show_tuning_windows)
{
  if (show_tuning_windows) {
    ensureTuningWindows();
  } else {
    closeTuningWindows();
  }

  rebuildTemplatesIfNeeded();

  const cv::Mat mask = preprocess(image);
  cv::Mat grouped;
  std::vector<Candidate> candidates = findCandidates(mask, show_tuning_windows ? &grouped : nullptr);

  std::vector<std::pair<Detection, MatchResult>> accepted;
  for (const auto & candidate : candidates) {
    const MatchResult match = matchCandidate(candidate);
    if (!match.accepted) {
      continue;
    }

    Detection det;
    det.class_id = match.class_id;
    det.score = match.score;
    det.bbox = cv::Rect2f(candidate.bbox);
    det.has_bbox = true;
    det.corners = candidate.corners;
    det.has_keypoints = false;
    det.corner_source = CornerSource::BBOX;
    accepted.push_back({det, match});
  }

  std::sort(accepted.begin(), accepted.end(),
    [](const auto & a, const auto & b) {
      return a.first.score > b.first.score;
    });

  std::vector<Detection> detections;
  detections.reserve(accepted.size());
  for (const auto & item : accepted) {
    detections.push_back(item.first);
  }

  if (show_tuning_windows) {
    cv::imshow("traditional_qr_mask", mask);
    if (!grouped.empty()) {
      cv::imshow("traditional_qr_grouped", grouped);
    }
  }

  return detections;
}

}  // namespace smarthome_vision
