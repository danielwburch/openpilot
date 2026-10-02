#include "selfdrive/ui/qt/onroad/driver_monitoring.h"
#include <algorithm>
#include <cmath>

#include "selfdrive/ui/qt/onroad/buttons.h"
#include "selfdrive/ui/qt/util.h"

// 3D keypoints for the middle finger outline, drawn as separate strokes:
// folded index finger, folded ring finger, hand body, raised middle finger.
// Traced from Tabler Icons "hand-middle-finger" (MIT), scaled to the frame the face outline used,
// and centered on the bounding box so it sits in the middle of the circle.
static const std::vector<std::vector<vec3>> DEFAULT_FACE_KPTS_3D = {
  {{{-18.80, 4.95, 8.00}}, {{-18.80, 0.59, 8.00}}, {{-18.80, -3.76, 8.00}}, {{-18.78, -8.12, 8.00}}, {{-17.24, -12.13, 8.00}},
   {{-13.76, -14.64, 8.00}}, {{-9.47, -14.82, 8.00}}, {{-5.78, -12.62, 8.00}}, {{-3.90, -8.76, 8.00}}, {{-3.80, -4.41, 8.00}},
   {{-3.80, -0.05, 8.00}}},
  {{{11.20, -7.55, 8.00}}, {{12.18, -11.26, 8.00}}, {{14.87, -14.00, 8.00}}, {{18.56, -15.05, 8.00}}, {{22.29, -14.13, 8.00}},
   {{25.08, -11.49, 8.00}}, {{26.19, -7.82, 8.00}}, {{26.20, -3.93, 8.00}}, {{26.20, -0.05, 8.00}}},
  {{{26.20, -2.55, 8.00}}, {{27.85, -7.25, 8.00}}, {{32.08, -9.88, 8.00}}, {{37.02, -9.27, 8.00}}, {{40.50, -5.71, 8.00}},
   {{41.20, -0.73, 8.00}}, {{41.20, 4.34, 8.00}}, {{41.20, 9.42, 8.00}}, {{41.20, 14.49, 8.00}}, {{41.20, 19.57, 8.00}},
   {{40.83, 24.63, 8.00}}, {{39.62, 29.55, 8.00}}, {{37.60, 34.20, 8.00}}, {{34.82, 38.44, 8.00}}, {{31.37, 42.15, 8.00}},
   {{27.34, 45.23, 8.00}}, {{22.85, 47.59, 8.00}}, {{18.03, 49.16, 8.00}}, {{13.02, 49.89, 8.00}}, {{7.94, 49.95, 8.00}},
   {{2.86, 49.95, 8.00}}, {{-0.13, 49.86, 8.00}}, {{-5.13, 49.03, 8.00}}, {{-9.92, 47.38, 8.00}}, {{-14.37, 44.94, 8.00}},
   {{-18.34, 41.79, 8.00}}, {{-21.72, 38.01, 8.00}}, {{-24.02, 34.61, 8.00}}, {{-25.17, 32.73, 8.00}}, {{-26.87, 29.83, 8.00}},
   {{-29.13, 25.91, 8.00}}, {{-31.94, 20.99, 8.00}}, {{-35.31, 15.04, 8.00}}, {{-39.23, 8.09, 8.00}}, {{-41.20, 2.59, 8.00}},
   {{-39.52, -2.10, 8.00}}, {{-35.30, -4.78, 8.00}}, {{-30.29, -4.80, 8.00}}, {{-25.98, -2.23, 8.00}}, {{-22.39, 1.36, 8.00}},
   {{-18.80, 4.95, 8.00}}},
  {{{-3.80, -2.55, 8.00}}, {{-3.80, -9.18, 8.00}}, {{-3.80, -15.81, 8.00}}, {{-3.80, -22.44, 8.00}}, {{-3.80, -29.07, 8.00}},
   {{-3.80, -35.70, 8.00}}, {{-3.80, -42.33, 8.00}}, {{-1.23, -48.20, 8.00}}, {{4.94, -49.95, 8.00}}, {{10.20, -46.28, 8.00}},
   {{11.20, -39.83, 8.00}}, {{11.20, -33.20, 8.00}}, {{11.20, -26.57, 8.00}}, {{11.20, -19.94, 8.00}}, {{11.20, -13.31, 8.00}},
   {{11.20, -6.68, 8.00}}, {{11.20, -0.05, 8.00}}},
};

static const QColor DMON_OUTLINE_COLOR = QColor::fromRgbF(1.0, 0.0, 0.0);

DriverMonitorRenderer::DriverMonitorRenderer() : face_kpts_draw(DEFAULT_FACE_KPTS_3D) {}

void DriverMonitorRenderer::updateState(const UIState &s) {
  auto &sm = *(s.sm);
  is_visible = sm["selfdriveState"].getSelfdriveState().getAlertSize() == cereal::SelfdriveState::AlertSize::NONE &&
               sm.rcv_frame("driverStateV2") > s.scene.started_frame;
  if (!is_visible) return;

  auto dm_state = sm["driverMonitoringState"].getDriverMonitoringState();
  is_active = dm_state.getIsActiveMode();
  is_rhd = dm_state.getIsRHD();
  dm_fade_state = std::clamp(dm_fade_state + 0.2f * (0.5f - is_active), 0.0f, 1.0f);

  const auto &driverstate = sm["driverStateV2"].getDriverStateV2();
  const auto driver_orient = is_rhd ? driverstate.getRightDriverData().getFaceOrientation() : driverstate.getLeftDriverData().getFaceOrientation();

  for (int i = 0; i < 3; ++i) {
    float v_this = (i == 0 ? (driver_orient[i] < 0 ? 0.7 : 0.9) : 0.4) * driver_orient[i];
    driver_pose_vals[i] = 0.8f * v_this + (1 - 0.8) * driver_pose_vals[i];
    driver_pose_sins[i] = std::sin(driver_pose_vals[i] * (1.0f - dm_fade_state));
    driver_pose_coss[i] = std::cos(driver_pose_vals[i] * (1.0f - dm_fade_state));
  }

  auto [sin_y, sin_x, sin_z] = driver_pose_sins;
  auto [cos_y, cos_x, cos_z] = driver_pose_coss;

  // Rotation matrix for transforming keypoints based on driver's head orientation
  const mat3 r_xyz = {{
    cos_x * cos_z, cos_x * sin_z, -sin_x,
    -sin_y * sin_x * cos_z - cos_y * sin_z, -sin_y * sin_x * sin_z + cos_y * cos_z, -sin_y * cos_x,
    cos_y * sin_x * cos_z - sin_y * sin_z, cos_y * sin_x * sin_z + sin_y * cos_z, cos_y * cos_x,
  }};

  // Transform vertices of every stroke
  for (size_t i = 0; i < DEFAULT_FACE_KPTS_3D.size(); ++i) {
    for (size_t j = 0; j < DEFAULT_FACE_KPTS_3D[i].size(); ++j) {
      vec3 kpt = matvecmul3(r_xyz, DEFAULT_FACE_KPTS_3D[i][j]);
      face_kpts_draw[i][j] = {{kpt.v[0], kpt.v[1], kpt.v[2] * (1.0f - dm_fade_state) + 8 * dm_fade_state}};
    }
  }
}

void DriverMonitorRenderer::draw(QPainter &painter, const QRect &surface_rect) {
  if (!is_visible) return;

  painter.save();

  int offset = UI_BORDER_SIZE + btn_size / 2;
  float x = is_rhd ? surface_rect.width() - offset : offset;
  float y = surface_rect.height() - offset;
  float opacity = is_active ? 0.65f : 0.2f;

  // translucent backdrop circle
  painter.setPen(Qt::NoPen);
  painter.setBrush(QColor(0, 0, 0, 70));
  painter.drawEllipse(QPointF(x, y), btn_size / 2.0, btn_size / 2.0);

  // red middle finger outline, rotated with the driver's head
  QColor outline_color = DMON_OUTLINE_COLOR;
  outline_color.setAlphaF(opacity);
  painter.setPen(QPen(outline_color, 5.2, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
  painter.setBrush(Qt::NoBrush);
  for (const auto &stroke : face_kpts_draw) {
    std::vector<QPointF> keypoints(stroke.size());
    for (size_t i = 0; i < stroke.size(); ++i) {
      const auto &v = stroke[i].v;
      float kp = (v[2] - 8) / 120.0f + 1.0f;
      keypoints[i] = QPointF(v[0] * kp + x, v[1] * kp + y);
    }
    painter.drawPolyline(keypoints.data(), static_cast<int>(keypoints.size()));
  }

  painter.restore();
}
