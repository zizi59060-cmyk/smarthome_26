#include "cuda_pointcloud_preprocessor/cuda_filter.hpp"

#include <algorithm>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"

namespace cuda_pointcloud_preprocessor
{

class CudaPointcloudPreprocessorNode : public rclcpp::Node
{
public:
  explicit CudaPointcloudPreprocessorNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions())
  : Node("cuda_pointcloud_preprocessor", options)
  {
    input_topic_ = declare_parameter<std::string>("input_topic", "registered_scan");
    output_topic_ = declare_parameter<std::string>("output_topic", "registered_scan_filtered");
    frame_id_override_ = declare_parameter<std::string>("frame_id_override", "");
    prefer_cuda_ = declare_parameter<bool>("prefer_cuda", true);
    stride_ = std::max(1, declare_parameter<int>("stride", 1));
    config_.min_x = declare_parameter<double>("min_x", -std::numeric_limits<float>::infinity());
    config_.max_x = declare_parameter<double>("max_x", std::numeric_limits<float>::infinity());
    config_.min_y = declare_parameter<double>("min_y", -std::numeric_limits<float>::infinity());
    config_.max_y = declare_parameter<double>("max_y", std::numeric_limits<float>::infinity());
    config_.min_z = declare_parameter<double>("min_z", -1.5);
    config_.max_z = declare_parameter<double>("max_z", 2.0);
    config_.min_range = declare_parameter<double>("min_range", 0.35);
    config_.max_range = declare_parameter<double>("max_range", 10.0);
    config_.min_intensity = declare_parameter<double>("min_intensity", -std::numeric_limits<float>::infinity());
    config_.max_intensity = declare_parameter<double>("max_intensity", std::numeric_limits<float>::infinity());

    use_cuda_ = prefer_cuda_ && cudaAvailable();
    RCLCPP_INFO(
      get_logger(), "Point cloud preprocessor using %s path: %s -> %s",
      use_cuda_ ? "CUDA" : "CPU", input_topic_.c_str(), output_topic_.c_str());

    publisher_ = create_publisher<sensor_msgs::msg::PointCloud2>(output_topic_, rclcpp::SensorDataQoS());
    subscription_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      input_topic_, rclcpp::SensorDataQoS(),
      std::bind(&CudaPointcloudPreprocessorNode::onCloud, this, std::placeholders::_1));
  }

private:
  static bool hasField(const sensor_msgs::msg::PointCloud2 & msg, const std::string & name)
  {
    return std::any_of(msg.fields.begin(), msg.fields.end(), [&](const auto & field) {
      return field.name == name;
    });
  }

  void onCloud(const sensor_msgs::msg::PointCloud2::ConstSharedPtr msg)
  {
    if (!hasField(*msg, "x") || !hasField(*msg, "y") || !hasField(*msg, "z")) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000, "Input cloud is missing x/y/z fields; dropping frame");
      return;
    }

    input_points_.clear();
    const auto point_count = static_cast<std::size_t>(msg->width) * static_cast<std::size_t>(msg->height);
    input_points_.reserve(point_count / static_cast<std::size_t>(stride_) + 1);

    const bool has_intensity = hasField(*msg, "intensity");
    sensor_msgs::PointCloud2ConstIterator<float> iter_x(*msg, "x");
    sensor_msgs::PointCloud2ConstIterator<float> iter_y(*msg, "y");
    sensor_msgs::PointCloud2ConstIterator<float> iter_z(*msg, "z");
    std::unique_ptr<sensor_msgs::PointCloud2ConstIterator<float>> iter_intensity;
    if (has_intensity) {
      iter_intensity = std::make_unique<sensor_msgs::PointCloud2ConstIterator<float>>(*msg, "intensity");
    }

    int stride_counter = 0;
    for (; iter_x != iter_x.end(); ++iter_x, ++iter_y, ++iter_z) {
      if ((stride_counter++ % stride_) != 0) {
        if (iter_intensity) {
          ++(*iter_intensity);
        }
        continue;
      }

      input_points_.push_back(
        PointXYZI{*iter_x, *iter_y, *iter_z, iter_intensity ? **iter_intensity : 0.0f});

      if (iter_intensity) {
        ++(*iter_intensity);
      }
    }

    if (use_cuda_) {
      filterCuda(input_points_, output_points_, config_);
    } else {
      filterCpu(input_points_, output_points_, config_);
    }

    sensor_msgs::msg::PointCloud2 out;
    out.header = msg->header;
    if (!frame_id_override_.empty()) {
      out.header.frame_id = frame_id_override_;
    }

    sensor_msgs::PointCloud2Modifier modifier(out);
    modifier.setPointCloud2Fields(
      4,
      "x", 1, sensor_msgs::msg::PointField::FLOAT32,
      "y", 1, sensor_msgs::msg::PointField::FLOAT32,
      "z", 1, sensor_msgs::msg::PointField::FLOAT32,
      "intensity", 1, sensor_msgs::msg::PointField::FLOAT32);
    modifier.resize(output_points_.size());

    sensor_msgs::PointCloud2Iterator<float> out_x(out, "x");
    sensor_msgs::PointCloud2Iterator<float> out_y(out, "y");
    sensor_msgs::PointCloud2Iterator<float> out_z(out, "z");
    sensor_msgs::PointCloud2Iterator<float> out_intensity(out, "intensity");
    for (const auto & point : output_points_) {
      *out_x = point.x;
      *out_y = point.y;
      *out_z = point.z;
      *out_intensity = point.intensity;
      ++out_x;
      ++out_y;
      ++out_z;
      ++out_intensity;
    }

    publisher_->publish(out);
  }

  std::string input_topic_;
  std::string output_topic_;
  std::string frame_id_override_;
  bool prefer_cuda_{true};
  bool use_cuda_{false};
  int stride_{1};
  FilterConfig config_{};
  std::vector<PointXYZI> input_points_;
  std::vector<PointXYZI> output_points_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr subscription_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr publisher_;
};

}  // namespace cuda_pointcloud_preprocessor

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<cuda_pointcloud_preprocessor::CudaPointcloudPreprocessorNode>());
  rclcpp::shutdown();
  return 0;
}
