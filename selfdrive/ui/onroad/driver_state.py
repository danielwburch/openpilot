import numpy as np
import pyray as rl
from openpilot.selfdrive.ui.ui_state import ui_state, UI_BORDER_SIZE
from openpilot.system.ui.widgets import Widget

# 3D keypoints for the middle finger outline, as separate strokes:
# folded index finger, folded ring finger, hand body, raised middle finger.
# Traced from Tabler Icons "hand-middle-finger" (MIT), scaled to the frame the face outline used,
# and centered on the bounding box so it sits in the middle of the circle.
DEFAULT_FACE_STROKES_3D = [np.array(s, dtype=np.float32) for s in (
  [[-18.80, 4.95, 8.00], [-18.80, 0.59, 8.00], [-18.80, -3.76, 8.00], [-18.78, -8.12, 8.00], [-17.24, -12.13, 8.00],
   [-13.76, -14.64, 8.00], [-9.47, -14.82, 8.00], [-5.78, -12.62, 8.00], [-3.90, -8.76, 8.00], [-3.80, -4.41, 8.00],
   [-3.80, -0.05, 8.00]],
  [[11.20, -7.55, 8.00], [12.18, -11.26, 8.00], [14.87, -14.00, 8.00], [18.56, -15.05, 8.00], [22.29, -14.13, 8.00],
   [25.08, -11.49, 8.00], [26.19, -7.82, 8.00], [26.20, -3.93, 8.00], [26.20, -0.05, 8.00]],
  [[26.20, -2.55, 8.00], [27.85, -7.25, 8.00], [32.08, -9.88, 8.00], [37.02, -9.27, 8.00], [40.50, -5.71, 8.00],
   [41.20, -0.73, 8.00], [41.20, 4.34, 8.00], [41.20, 9.42, 8.00], [41.20, 14.49, 8.00], [41.20, 19.57, 8.00],
   [40.83, 24.63, 8.00], [39.62, 29.55, 8.00], [37.60, 34.20, 8.00], [34.82, 38.44, 8.00], [31.37, 42.15, 8.00],
   [27.34, 45.23, 8.00], [22.85, 47.59, 8.00], [18.03, 49.16, 8.00], [13.02, 49.89, 8.00], [7.94, 49.95, 8.00],
   [2.86, 49.95, 8.00], [-0.13, 49.86, 8.00], [-5.13, 49.03, 8.00], [-9.92, 47.38, 8.00], [-14.37, 44.94, 8.00],
   [-18.34, 41.79, 8.00], [-21.72, 38.01, 8.00], [-24.02, 34.61, 8.00], [-25.17, 32.73, 8.00], [-26.87, 29.83, 8.00],
   [-29.13, 25.91, 8.00], [-31.94, 20.99, 8.00], [-35.31, 15.04, 8.00], [-39.23, 8.09, 8.00], [-41.20, 2.59, 8.00],
   [-39.52, -2.10, 8.00], [-35.30, -4.78, 8.00], [-30.29, -4.80, 8.00], [-25.98, -2.23, 8.00], [-22.39, 1.36, 8.00],
   [-18.80, 4.95, 8.00]],
  [[-3.80, -2.55, 8.00], [-3.80, -9.18, 8.00], [-3.80, -15.81, 8.00], [-3.80, -22.44, 8.00], [-3.80, -29.07, 8.00],
   [-3.80, -35.70, 8.00], [-3.80, -42.33, 8.00], [-1.23, -48.20, 8.00], [4.94, -49.95, 8.00], [10.20, -46.28, 8.00],
   [11.20, -39.83, 8.00], [11.20, -33.20, 8.00], [11.20, -26.57, 8.00], [11.20, -19.94, 8.00], [11.20, -13.31, 8.00],
   [11.20, -6.68, 8.00], [11.20, -0.05, 8.00]],
)]

# UI constants
BTN_SIZE = 192

SCALES_POS = np.array([0.9, 0.4, 0.4], dtype=np.float32)
SCALES_NEG = np.array([0.7, 0.4, 0.4], dtype=np.float32)


class DriverStateRenderer(Widget):
  def __init__(self):
    super().__init__()
    # Initial state with NumPy arrays
    self.face_kpts_draw = [s.copy() for s in DEFAULT_FACE_STROKES_3D]
    self.is_active = False
    self.is_rhd = False
    self.dm_fade_state = 0.0
    self.last_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)
    self.driver_pose_vals = np.zeros(3, dtype=np.float32)
    self.driver_pose_sins = np.zeros(3, dtype=np.float32)
    self.driver_pose_coss = np.zeros(3, dtype=np.float32)
    self.face_keypoints_transformed = [np.zeros((s.shape[0], 2), dtype=np.float32) for s in DEFAULT_FACE_STROKES_3D]
    self.position_x: float = 0.0
    self.position_y: float = 0.0

    # Pre-allocate drawing arrays, one polyline per stroke
    self.face_lines = [[rl.Vector2(0, 0) for _ in range(len(s))] for s in DEFAULT_FACE_STROKES_3D]

    # Colors
    self.outline_color = rl.Color(255, 0, 0, 255)

    self.set_visible(lambda: (ui_state.sm.recv_frame['driverStateV2'] > ui_state.started_frame and
                              ui_state.sm.seen['driverMonitoringState']))

  def _render(self, rect):
    # Set opacity based on active state
    opacity = 0.65 if self.is_active else 0.2

    # Draw background circle
    rl.draw_circle(int(self.position_x), int(self.position_y), BTN_SIZE // 2, rl.Color(0, 0, 0, 70))

    # Draw the red middle finger outline, one stroke at a time
    self.outline_color.a = int(255 * opacity)
    for stroke in self.face_lines:
      rl.draw_spline_linear(stroke, len(stroke), 5.2, self.outline_color)

  def _update_state(self):
    """Update the driver monitoring state based on model data"""
    sm = ui_state.sm
    if not sm.updated["driverMonitoringState"]:
      if (self._rect.x != self.last_rect.x or self._rect.y != self.last_rect.y or
          self._rect.width != self.last_rect.width or self._rect.height != self.last_rect.height):
        self._pre_calculate_drawing_elements()
        self.last_rect = self._rect
      return

    # Get monitoring state
    dm_state = sm["driverMonitoringState"]
    self.is_active = dm_state.isActiveMode
    self.is_rhd = dm_state.isRHD

    # Update fade state (smoother transition between active/inactive)
    fade_target = 0.0 if self.is_active else 0.5
    self.dm_fade_state = np.clip(self.dm_fade_state + 0.2 * (fade_target - self.dm_fade_state), 0.0, 1.0)

    # Get driver orientation data from appropriate camera
    driverstate = sm["driverStateV2"]
    driver_data = driverstate.rightDriverData if self.is_rhd else driverstate.leftDriverData
    driver_orient = driver_data.faceOrientation

    # Update pose values with scaling and smoothing
    driver_orient = np.array(driver_orient)
    scales = np.where(driver_orient < 0, SCALES_NEG, SCALES_POS)
    v_this = driver_orient * scales
    self.driver_pose_vals = 0.8 * v_this + 0.2 * self.driver_pose_vals  # Smooth changes

    # Apply fade to rotation and compute sin/cos
    rotation_amount = self.driver_pose_vals * (1.0 - self.dm_fade_state)
    self.driver_pose_sins = np.sin(rotation_amount)
    self.driver_pose_coss = np.cos(rotation_amount)

    # Create rotation matrix for the 3D outline
    sin_y, sin_x, sin_z = self.driver_pose_sins
    cos_y, cos_x, cos_z = self.driver_pose_coss
    r_xyz = np.array(
      [
        [cos_x * cos_z, cos_x * sin_z, -sin_x],
        [-sin_y * sin_x * cos_z - cos_y * sin_z, -sin_y * sin_x * sin_z + cos_y * cos_z, -sin_y * cos_x],
        [cos_y * sin_x * cos_z - sin_y * sin_z, cos_y * sin_x * sin_z + sin_y * cos_z, cos_y * cos_x],
      ]
    )

    # Transform keypoints of every stroke using vectorized matrix multiplication
    for i, stroke in enumerate(DEFAULT_FACE_STROKES_3D):
      kpts = stroke @ r_xyz.T
      kpts[:, 2] = kpts[:, 2] * (1.0 - self.dm_fade_state) + 8 * self.dm_fade_state
      self.face_kpts_draw[i] = kpts

      # Pre-calculate the transformed keypoints
      kp_depth = (kpts[:, 2] - 8) / 120.0 + 1.0
      self.face_keypoints_transformed[i] = kpts[:, :2] * kp_depth[:, None]

    # Pre-calculate all drawing elements
    self._pre_calculate_drawing_elements()

  def _pre_calculate_drawing_elements(self):
    """Pre-calculate all drawing elements based on the current rectangle"""
    # Calculate position (bottom-left or bottom-right)
    width, height = self._rect.width, self._rect.height
    offset = UI_BORDER_SIZE + BTN_SIZE // 2
    self.position_x = self._rect.x + (width - offset if self.is_rhd else offset)
    self.position_y = self._rect.y + height - offset

    # Pre-calculate the outline positions for every stroke
    for s, transformed in enumerate(self.face_keypoints_transformed):
      positioned_keypoints = transformed + np.array([self.position_x, self.position_y])
      for i in range(len(positioned_keypoints)):
        self.face_lines[s][i].x = positioned_keypoints[i][0]
        self.face_lines[s][i].y = positioned_keypoints[i][1]
