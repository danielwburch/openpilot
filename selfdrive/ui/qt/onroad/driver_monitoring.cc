#include "selfdrive/ui/qt/onroad/driver_monitoring.h"
#include <algorithm>
#include <cmath>

#include "selfdrive/ui/qt/onroad/buttons.h"
#include "selfdrive/ui/qt/util.h"

// 3D keypoints for the middle finger outline, drawn as separate strokes:
// folded index finger, folded ring finger, hand body, raised middle finger.
// Traced from Tabler Icons "hand-middle-finger" (MIT) and scaled to the same frame the face outline used.
static const std::vector<std::vector<vec3>> DEFAULT_FACE_KPTS_3D = {
  {{{-17.50, 5.00, 8.00}}, {{-17.50, 0.64, 8.00}}, {{-17.50, -3.71, 8.00}}, {{-17.48, -8.07, 8.00}}, {{-15.94, -12.08, 8.00}},
   {{-12.45, -14.59, 8.00}}, {{-8.16, -14.77, 8.00}}, {{-4.47, -12.57, 8.00}}, {{-2.60, -8.71, 8.00}}, {{-2.50, -4.36, 8.00}},
   {{-2.50, 0.00, 8.00}}},
  {{{12.50, -7.50, 8.00}}, {{13.48, -11.21, 8.00}}, {{16.17, -13.95, 8.00}}, {{19.87, -15.00, 8.00}}, {{23.60, -14.08, 8.00}},
   {{26.38, -11.44, 8.00}}, {{27.50, -7.77, 8.00}}, {{27.50, -3.88, 8.00}}, {{27.50, 0.00, 8.00}}},
  {{{27.50, -2.50, 8.00}}, {{29.15, -7.20, 8.00}}, {{33.38, -9.82, 8.00}}, {{38.33, -9.22, 8.00}}, {{41.80, -5.66, 8.00}},
   {{42.50, -0.68, 8.00}}, {{42.50, 4.39, 8.00}}, {{42.50, 9.47, 8.00}}, {{42.50, 14.55, 8.00}}, {{42.50, 19.62, 8.00}},
   {{42.13, 24.68, 8.00}}, {{40.92, 29.60, 8.00}}, {{38.90, 34.25, 8.00}}, {{36.12, 38.49, 8.00}}, {{32.67, 42.21, 8.00}},
   {{28.64, 45.29, 8.00}}, {{24.16, 47.64, 8.00}}, {{19.34, 49.21, 8.00}}, {{14.32, 49.94, 8.00}}, {{9.24, 50.00, 8.00}},
   {{4.17, 50.00, 8.00}}, {{1.17, 49.91, 8.00}}, {{-3.83, 49.08, 8.00}}, {{-8.62, 47.43, 8.00}}, {{-13.06, 44.99, 8.00}},
   {{-17.04, 41.84, 8.00}}, {{-20.42, 38.06, 8.00}}, {{-22.71, 34.66, 8.00}}, {{-23.86, 32.78, 8.00}}, {{-25.56, 29.88, 8.00}},
   {{-27.82, 25.97, 8.00}}, {{-30.64, 21.04, 8.00}}, {{-34.00, 15.10, 8.00}}, {{-37.93, 8.14, 8.00}}, {{-39.89, 2.64, 8.00}},
   {{-38.21, -2.05, 8.00}}, {{-34.00, -4.73, 8.00}}, {{-28.98, -4.75, 8.00}}, {{-24.68, -2.18, 8.00}}, {{-21.09, 1.41, 8.00}},
   {{-17.50, 5.00, 8.00}}},
  {{{-2.50, -2.50, 8.00}}, {{-2.50, -9.13, 8.00}}, {{-2.50, -15.76, 8.00}}, {{-2.50, -22.39, 8.00}}, {{-2.50, -29.02, 8.00}},
   {{-2.50, -35.64, 8.00}}, {{-2.50, -42.27, 8.00}}, {{0.07, -48.15, 8.00}}, {{6.24, -49.90, 8.00}}, {{11.51, -46.23, 8.00}},
   {{12.50, -39.77, 8.00}}, {{12.50, -33.14, 8.00}}, {{12.50, -26.52, 8.00}}, {{12.50, -19.89, 8.00}}, {{12.50, -13.26, 8.00}},
   {{12.50, -6.63, 8.00}}, {{12.50, 0.00, 8.00}}},
};

// Colors used for drawing based on monitoring state
static const QColor DMON_ENGAGED_COLOR = QColor::fromRgbF(0.1, 0.945, 0.26);
static const QColor DMON_DISENGAGED_COLOR = QColor::fromRgbF(0.545, 0.545, 0.545);
static const QColor DMON_OUTLINE_COLOR = QColor::fromRgbF(1.0, 0.0, 0.0);

DriverMonitorRenderer::DriverMonitorRenderer() : face_kpts_draw(DEFAULT_FACE_KPTS_3D) {
  dm_img = loadPixmap("../assets/icons/middle_finger.png", {img_size + 5, img_size + 5});
}

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
    driver_pose_diff[i] = std::abs(driver_pose_vals[i] - v_this);
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

  drawIcon(painter, QPoint(x, y), dm_img, QColor(0, 0, 0, 70), opacity);

  QColor outline_color = DMON_OUTLINE_COLOR;
  outline_color.setAlphaF(opacity);
  painter.setPen(QPen(outline_color, 5.2, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
  for (const auto &stroke : face_kpts_draw) {
    std::vector<QPointF> keypoints(stroke.size());
    for (size_t i = 0; i < stroke.size(); ++i) {
      const auto &v = stroke[i].v;
      float kp = (v[2] - 8) / 120.0f + 1.0f;
      keypoints[i] = QPointF(v[0] * kp + x, v[1] * kp + y);
    }
    painter.drawPolyline(keypoints.data(), static_cast<int>(keypoints.size()));
  }

  // tracking arcs
  const int arc_l = 133;
  const float arc_t_default = 6.7f;
  const float arc_t_extend = 12.0f;
  QColor arc_color = uiState()->engaged() ? DMON_ENGAGED_COLOR : DMON_DISENGAGED_COLOR;
  arc_color.setAlphaF(0.4 * (1.0f - dm_fade_state));

  float delta_x = -driver_pose_sins[1] * arc_l / 2.0f;
  float delta_y = -driver_pose_sins[0] * arc_l / 2.0f;

  // Draw horizontal tracking arc
  painter.setPen(QPen(arc_color, arc_t_default + arc_t_extend * std::min(1.0, driver_pose_diff[1] * 5.0), Qt::SolidLine, Qt::RoundCap));
  painter.drawArc(QRectF(std::min(x + delta_x, x), y - arc_l / 2, std::abs(delta_x), arc_l), (driver_pose_sins[1] > 0 ? 90 : -90) * 16, 180 * 16);

  // Draw vertical tracking arc
  painter.setPen(QPen(arc_color, arc_t_default + arc_t_extend * std::min(1.0, driver_pose_diff[0] * 5.0), Qt::SolidLine, Qt::RoundCap));
  painter.drawArc(QRectF(x - arc_l / 2, std::min(y + delta_y, y), arc_l, std::abs(delta_y)), (driver_pose_sins[0] > 0 ? 0 : 180) * 16, 180 * 16);

  painter.restore();
}
