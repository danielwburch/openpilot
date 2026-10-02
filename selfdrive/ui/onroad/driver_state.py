import numpy as np
import pyray as rl
from dataclasses import dataclass
from openpilot.selfdrive.ui.ui_state import ui_state, UI_BORDER_SIZE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget

# 3D keypoints for the middle finger outline, as separate strokes:
# folded index finger, folded ring finger, hand body, raised middle finger.
# Traced from Tabler Icons "hand-middle-finger" (MIT) and scaled to the frame the face outline used.
DEFAULT_FACE_STROKES_3D = [np.array(s, dtype=np.float32) for s in (
  [[-17.50, 5.00, 8.00], [-17.50, 0.64, 8.00], [-17.50, -3.71, 8.00], [-17.48, -8.07, 8.00], [-15.94, -12.08, 8.00],
   [-12.45, -14.59, 8.00], [-8.16, -14.77, 8.00], [-4.47, -12.57, 8.00], [-2.60, -8.71, 8.00], [-2.50, -4.36, 8.00],
   [-2.50, 0.00, 8.00]],
  [[12.50, -7.50, 8.00], [13.48, -11.21, 8.00], [16.17, -13.95, 8.00], [19.87, -15.00, 8.00], [23.60, -14.08, 8.00],
   [26.38, -11.44, 8.00], [27.50, -7.77, 8.00], [27.50, -3.88, 8.00], [27.50, 0.00, 8.00]],
  [[27.50, -2.50, 8.00], [29.15, -7.20, 8.00], [33.38, -9.82, 8.00], [38.33, -9.22, 8.00], [41.80, -5.66, 8.00],
   [42.50, -0.68, 8.00], [42.50, 4.39, 8.00], [42.50, 9.47, 8.00], [42.50, 14.55, 8.00], [42.50, 19.62, 8.00],
   [42.13, 24.68, 8.00], [40.92, 29.60, 8.00], [38.90, 34.25, 8.00], [36.12, 38.49, 8.00], [32.67, 42.21, 8.00],
   [28.64, 45.29, 8.00], [24.16, 47.64, 8.00], [19.34, 49.21, 8.00], [14.32, 49.94, 8.00], [9.24, 50.00, 8.00],
   [4.17, 50.00, 8.00], [1.17, 49.91, 8.00], [-3.83, 49.08, 8.00], [-8.62, 47.43, 8.00], [-13.06, 44.99, 8.00],
   [-17.04, 41.84, 8.00], [-20.42, 38.06, 8.00], [-22.71, 34.66, 8.00], [-23.86, 32.78, 8.00], [-25.56, 29.88, 8.00],
   [-27.82, 25.97, 8.00], [-30.64, 21.04, 8.00], [-34.00, 15.10, 8.00], [-37.93, 8.14, 8.00], [-39.89, 2.64, 8.00],
   [-38.21, -2.05, 8.00], [-34.00, -4.73, 8.00], [-28.98, -4.75, 8.00], [-24.68, -2.18, 8.00], [-21.09, 1.41, 8.00],
   [-17.50, 5.00, 8.00]],
  [[-2.50, -2.50, 8.00], [-2.50, -9.13, 8.00], [-2.50, -15.76, 8.00], [-2.50, -22.39, 8.00], [-2.50, -29.02, 8.00],
   [-2.50, -35.64, 8.00], [-2.50, -42.27, 8.00], [0.07, -48.15, 8.00], [6.24, -49.90, 8.00], [11.51, -46.23, 8.00],
   [12.50, -39.77, 8.00], [12.50, -33.14, 8.00], [12.50, -26.52, 8.00], [12.50, -19.89, 8.00], [12.50, -13.26, 8.00],
   [12.50, -6.63, 8.00], [12.50, 0.00, 8.00]],
)]

# UI constants
BTN_SIZE = 192
IMG_SIZE = 144
ARC_LENGTH = 133
ARC_THICKNESS_DEFAULT = 6.7
ARC_THICKNESS_EXTEND = 12.0

SCALES_POS = np.array([0.9, 0.4, 0.4], dtype=np.float32)
SCALES_NEG = np.array([0.7, 0.4, 0.4], dtype=np.float32)

ARC_POINT_COUNT = 37  # Number of points in the arc
ARC_ANGLES = np.linspace(0.0, np.pi, ARC_POINT_COUNT, dtype=np.float32)


@dataclass
class ArcData:
  """Data structure for arc rendering parameters."""
  x: float
  y: float
  width: float
  height: float
  thickness: float


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
    self.driver_pose_diff = np.zeros(3, dtype=np.float32)
    self.driver_pose_sins = np.zeros(3, dtype=np.float32)
    self.driver_pose_coss = np.zeros(3, dtype=np.float32)
    self.face_keypoints_transformed = [np.zeros((s.shape[0], 2), dtype=np.float32) for s in DEFAULT_FACE_STROKES_3D]
    self.position_x: float = 0.0
    self.position_y: float = 0.0
    self.h_arc_data = None
    self.v_arc_data = None

    # Pre-allocate drawing arrays
    self.face_lines = [[rl.Vector2(0, 0) for _ in range(len(s))] for s in DEFAULT_FACE_STROKES_3D]
    self.h_arc_lines = [rl.Vector2(0, 0) for _ in range(ARC_POINT_COUNT)]
    self.v_arc_lines = [rl.Vector2(0, 0) for _ in range(ARC_POINT_COUNT)]

    # Load the middle finger icon
    self.dm_img = gui_app.texture("icons/middle_finger.png", IMG_SIZE, IMG_SIZE)

    # Colors
    self.outline_color = rl.Color(255, 0, 0, 255)
    self.arc_color = rl.Color(26, 242, 66, 255)
    self.engaged_color = rl.Color(26, 242, 66, 255)
    self.disengaged_color = rl.Color(139, 139, 139, 255)

    self.set_visible(lambda: (ui_state.sm.recv_frame['driverStateV2'] > ui_state.started_frame and
                              ui_state.sm.seen['driverMonitoringState']))

  def _render(self, rect):
    # Set opacity based on active state
    opacity = 0.65 if self.is_active else 0.2

    # Draw background circle
    rl.draw_circle(int(self.position_x), int(self.position_y), BTN_SIZE // 2, rl.Color(0, 0, 0, 70))

    # Draw face icon
    icon_pos = rl.Vector2(self.position_x - self.dm_img.width // 2, self.position_y - self.dm_img.height // 2)
    rl.draw_texture_v(self.dm_img, icon_pos, rl.Color(255, 255, 255, int(255 * opacity)))

    # Draw the middle finger outline, one stroke at a time
    self.outline_color.a = int(255 * opacity)
    for stroke in self.face_lines:
      rl.draw_spline_linear(stroke, len(stroke), 5.2, self.outline_color)

    # Set arc color based on engaged state
    self.arc_color = self.engaged_color if ui_state.engaged else self.disengaged_color
    self.arc_color.a = int(0.4 * 255 * (1.0 - self.dm_fade_state))  # Fade out when inactive

    # Draw arcs
    if self.h_arc_data:
      rl.draw_spline_linear(self.h_arc_lines, len(self.h_arc_lines), self.h_arc_data.thickness, self.arc_color)
    if self.v_arc_data:
      rl.draw_spline_linear(self.v_arc_lines, len(self.v_arc_lines), self.v_arc_data.thickness, self.arc_color)

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
    self.driver_pose_diff = np.abs(self.driver_pose_vals - v_this)
    self.driver_pose_vals = 0.8 * v_this + 0.2 * self.driver_pose_vals  # Smooth changes

    # Apply fade to rotation and compute sin/cos
    rotation_amount = self.driver_pose_vals * (1.0 - self.dm_fade_state)
    self.driver_pose_sins = np.sin(rotation_amount)
    self.driver_pose_coss = np.cos(rotation_amount)

    # Create rotation matrix for 3D face model
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
    # Calculate icon position (bottom-left or bottom-right)
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

    # Calculate arc dimensions based on head rotation
    delta_x = -self.driver_pose_sins[1] * ARC_LENGTH / 2.0  # Horizontal movement
    delta_y = -self.driver_pose_sins[0] * ARC_LENGTH / 2.0  # Vertical movement

    # Horizontal arc
    h_width = abs(delta_x)
    self.h_arc_data = self._calculate_arc_data(
      delta_x, h_width, self.position_x, self.position_y - ARC_LENGTH / 2,
      self.driver_pose_sins[1], self.driver_pose_diff[1], is_horizontal=True
    )

    # Vertical arc
    v_height = abs(delta_y)
    self.v_arc_data = self._calculate_arc_data(
      delta_y, v_height, self.position_x - ARC_LENGTH / 2, self.position_y,
      self.driver_pose_sins[0], self.driver_pose_diff[0], is_horizontal=False
    )

  def _calculate_arc_data(
    self, delta: float, size: float, x: float, y: float, sin_val: float, diff_val: float, is_horizontal: bool
  ):
    """Calculate arc data and pre-compute arc points."""
    if size <= 0:
      return None

    thickness = ARC_THICKNESS_DEFAULT + ARC_THICKNESS_EXTEND * min(1.0, diff_val * 5.0)
    start_angle = (90 if sin_val > 0 else -90) if is_horizontal else (0 if sin_val > 0 else 180)
    x = min(x + delta, x) if is_horizontal else x
    y = y if is_horizontal else min(y + delta, y)

    arc_data = ArcData(
      x=x,
      y=y,
      width=size if is_horizontal else ARC_LENGTH,
      height=ARC_LENGTH if is_horizontal else size,
      thickness=thickness,
    )

    # Pre-calculate arc points
    angles = ARC_ANGLES + np.deg2rad(start_angle)

    center_x = x + arc_data.width / 2
    center_y = y + arc_data.height / 2
    radius_x = arc_data.width / 2
    radius_y = arc_data.height / 2

    x_coords = center_x + np.cos(angles) * radius_x
    y_coords = center_y + np.sin(angles) * radius_y

    arc_lines = self.h_arc_lines if is_horizontal else self.v_arc_lines
    for i, (x_coord, y_coord) in enumerate(zip(x_coords, y_coords, strict=True)):
      arc_lines[i].x = x_coord
      arc_lines[i].y = y_coord

    return arc_data
