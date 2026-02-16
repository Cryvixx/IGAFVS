import sys
import math
import json
from pathlib import Path

import numpy as np
import sympy
from sympy import symbols, sympify, lambdify, sin, cos, tan, cot, sqrt, Abs, pi, E

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QInputDialog
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush

from hover_toolbar import HoverToolbar, set_i18n
from drawing_objects import DrawingObjects
from localization import Localization

# Глобальный объект локализации (создаётся один раз)
i18n = Localization('en')

# ВОТ ЭТА СТРОКА - передаём i18n в hover_toolbar! (оно не работает с простым импортом)
# Конечно, оно же не в классе даже (я не буду это менять)
set_i18n(i18n)

class DrawingCanvas(QWidget):
    """Основной холст для рисования графиков и геометрических фигур"""
    
    def __init__(self):
        super().__init__()
        
        # Объекты и функции
        self.objects = []
        self.functions = {}
        self.points = []
        self.x = symbols('x')
        
        # Текущее состояние инструмента
        self.current_tool = None
        self.start_pos = None
        self.temp_object = None
        self.angle_points = []
        self.text_items = []
        
        # Камера и зум
        self.base_grid_size = 50
        self.zoom_factor = 1.0
        self.min_zoom = 0.01
        self.max_zoom = 10.0
        self.show_grid = True
        
        # Панорамирование
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_panning = False
        self.last_pan_pos = None
        
        # Координаты мыши
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_world_x = 0.0
        self.mouse_world_y = 0.0
        
        # Система прилипания (snap)
        self.snap_point = None
        self.snap_radius = 15
        
        # Настройки виджета
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: white;")
        self.setFocusPolicy(Qt.StrongFocus)
        
        print(i18n.get('msg_initialized'))

    # ========== УПРАВЛЕНИЕ ИНСТРУМЕНТАМИ ==========

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name
        print(f"{i18n.get('msg_tool_changed')}{tool_name}")

    def add_function(self, function_text):
        func_index = len(self.functions)
        self._process_function(function_text, func_index)

    def _process_function(self, function_text, func_index):
        """Парсим и компилируем функцию с помощью sympy"""
        try:
            processed_text = self._preprocess_function(function_text)
            
            if 'x' not in processed_text:
                expr = sympify(processed_text)
                const_value = float(expr)
                func = lambda x_vals: np.full_like(np.asarray(x_vals), const_value, dtype=float)
            else:
                expr = sympify(processed_text)
                func = lambdify(
                    self.x, expr,
                    modules=[{
                        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                        'cot': lambda x: 1/np.tan(x),
                        'ctg': lambda x: 1/np.tan(x),
                        'sqrt': np.sqrt, 'abs': np.abs, 'Abs': np.abs,
                        'pi': np.pi, 'e': np.e,
                    }, 'numpy']
                )
            
            self.functions[func_index] = {
                'expr': expr,
                'func': func,
                'text': function_text,
                'visible': True,
                'color': self._get_color_for_index(func_index)
            }
            self.update()
            
        except Exception as e:
            msg = i18n.get('msg_function_error').format(function_text, str(e))
            print(msg)

    def _preprocess_function(self, func_text):
        """Преобразуем пользовательские обозначения в Python-синтаксис"""
        func_text = func_text.replace('^', '**')
        func_text = func_text.replace('cot(', '(1/tan(')
        func_text = func_text.replace('ctg(', '(1/tan(')
        cot_count = func_text.count('(1/tan(')
        func_text += ')' * cot_count
        return func_text

    def _get_color_for_index(self, index):
        colors = [
            QColor(40, 200, 40),
            QColor(255, 0, 0),
            QColor(0, 100, 255),
            QColor(255, 165, 0),
            QColor(160, 32, 240),
            QColor(220, 20, 60),
            QColor(0, 206, 209),
            QColor(184, 134, 11),
        ]
        return colors[index % len(colors)]

    def delete_function(self, func_index):
        if func_index in self.functions:
            del self.functions[func_index]
            self.update()

    def toggle_function(self, func_index, visible):
        if func_index in self.functions:
            self.functions[func_index]['visible'] = visible
            self.update()

    # ========== СИСТЕМА ПРИЛИПАНИЯ (SNAP) ==========

    def find_snap_point(self, world_x, world_y):
        """Ищет ближайшую "важную" точку для прилипания"""
        snap_points = []
        snap_points.extend(self._find_function_intersections(world_x, world_y))
        snap_points.extend(self._find_axis_intersections(world_x, world_y))
        snap_points.extend(self._find_existing_points(world_x, world_y))
        snap_points.extend(self._find_circle_centers(world_x, world_y))
        
        if self.current_tool == 'point':
            snap_points.extend(self._find_figure_sides(world_x, world_y))
        
        if snap_points:
            snap_points.sort(key=lambda p: p['distance'])
            return snap_points[0]
        
        return None

    def _find_function_intersections(self, world_x, world_y):
        snap_points = []
        snap_range = self.snap_radius / self.get_grid_size()
        func_list = list(self.functions.values())
        
        for i in range(len(func_list)):
            for j in range(i + 1, len(func_list)):
                if not func_list[i]['visible'] or not func_list[j]['visible']:
                    continue
                
                try:
                    x_min, x_max = world_x - snap_range, world_x + snap_range
                    x_test = np.linspace(x_min, x_max, 100)
                    y1 = func_list[i]['func'](x_test)
                    y2 = func_list[j]['func'](x_test)
                    
                    diff = np.abs(y1 - y2)
                    indices = np.where(diff < snap_range)[0]
                    
                    for idx in indices:
                        if np.isfinite(y1[idx]) and np.isfinite(y2[idx]):
                            px, py = x_test[idx], (y1[idx] + y2[idx]) / 2
                            dist = math.sqrt((px - world_x)**2 + (py - world_y)**2)
                            
                            if dist < snap_range:
                                snap_points.append({
                                    'x': px, 'y': py, 'distance': dist,
                                    'type': 'intersection'
                                })
                except:
                    pass
        
        return snap_points

    def _find_axis_intersections(self, world_x, world_y):
        snap_points = []
        snap_range = self.snap_radius / self.get_grid_size()
        
        for func_data in self.functions.values():
            if not func_data['visible']:
                continue
            
            try:
                func = func_data['func']
                x_min, x_max = world_x - snap_range, world_x + snap_range
                x_test = np.linspace(x_min, x_max, 100)
                y_test = func(x_test)
                
                indices = np.where(np.abs(y_test) < snap_range)[0]
                for idx in indices:
                    if np.isfinite(y_test[idx]):
                        px, py = x_test[idx], y_test[idx]
                        dist = math.sqrt((px - world_x)**2 + (py - world_y)**2)
                        
                        if dist < snap_range:
                            snap_points.append({
                                'x': px, 'y': py, 'distance': dist,
                                'type': 'axis_intersection'
                            })
                
                try:
                    y_at_zero = func(0)
                    if np.isfinite(y_at_zero) and abs(y_at_zero - world_y) < snap_range:
                        dist = abs(y_at_zero - world_y)
                        snap_points.append({
                            'x': 0, 'y': y_at_zero, 'distance': dist,
                            'type': 'axis_intersection'
                        })
                except:
                    pass
                    
            except:
                pass
        
        return snap_points

    def _find_existing_points(self, world_x, world_y):
        snap_points = []
        snap_range = self.snap_radius / self.get_grid_size()
        
        for i, point in enumerate(self.points):
            px, py = point['pos']
            dist = math.sqrt((px - world_x)**2 + (py - world_y)**2)
            if dist < snap_range:
                snap_points.append({
                    'x': px, 'y': py, 'distance': dist,
                    'type': 'point', 'point_index': i
                })
        
        return snap_points

    def _find_circle_centers(self, world_x, world_y):
        snap_points = []
        snap_range = self.snap_radius / self.get_grid_size()
        
        for obj in self.objects:
            if obj['type'] == 'circle':
                cx, cy = obj['center']
                dist = math.sqrt((cx - world_x)**2 + (cy - world_y)**2)
                if dist < snap_range:
                    snap_points.append({
                        'x': cx, 'y': cy, 'distance': dist,
                        'type': 'circle_center'
                    })
        
        return snap_points

    def _find_figure_sides(self, world_x, world_y):
        snap_points = []
        snap_range = self.snap_radius / self.get_grid_size()
        
        for obj in self.objects:
            if obj['type'] == 'line':
                x1, y1 = obj['points'][:2]
                x2, y2 = obj['points'][2:]
                
                closest = self._closest_point_on_line(world_x, world_y, x1, y1, x2, y2)
                if closest:
                    cx, cy, dist = closest
                    if dist < snap_range:
                        snap_points.append({
                            'x': cx, 'y': cy, 'distance': dist,
                            'type': 'line_point'
                        })
            
            elif obj['type'] == 'polygon':
                points = obj['points']
                for j in range(len(points)):
                    x1, y1 = points[j]
                    x2, y2 = points[(j + 1) % len(points)]
                    
                    closest = self._closest_point_on_line(world_x, world_y, x1, y1, x2, y2)
                    if closest:
                        cx, cy, dist = closest
                        if dist < snap_range:
                            snap_points.append({
                                'x': cx, 'y': cy, 'distance': dist,
                                'type': 'polygon_point'
                            })
        
        return snap_points

    def _closest_point_on_line(self, px, py, x1, y1, x2, y2):
        """Ищет ближайшую точку на отрезке"""
        dx, dy = x2 - x1, y2 - y1
        
        if dx == 0 and dy == 0:
            dist = math.sqrt((px - x1)**2 + (py - y1)**2)
            return (x1, y1, dist)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        dist = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
        
        return (closest_x, closest_y, dist)

    # ========== ПОИСК ОБЪЕКТОВ ==========

    def find_object_at_point(self, world_x, world_y):
        """Определяет какой объект находится в позиции"""
        search_radius = self.snap_radius / self.get_grid_size()
        
        for i, point in enumerate(self.points):
            px, py = point['pos']
            dist = math.sqrt((px - world_x)**2 + (py - world_y)**2)
            if dist < search_radius:
                return ('point', i)
        
        for i, obj in enumerate(self.objects):
            if obj['type'] == 'line':
                x1, y1 = obj['points'][:2]
                x2, y2 = obj['points'][2:]
                dist = self._point_to_line_distance(world_x, world_y, x1, y1, x2, y2)
                if dist < search_radius * 2:
                    return ('line', i)
            
            elif obj['type'] == 'circle':
                cx, cy = obj['center']
                r = obj['radius']
                dist_to_center = math.sqrt((world_x - cx)**2 + (world_y - cy)**2)
                if abs(dist_to_center - r) < search_radius * 2:
                    return ('circle', i)
            
            elif obj['type'] == 'polygon':
                points = obj['points']
                for j in range(len(points)):
                    x1, y1 = points[j]
                    x2, y2 = points[(j + 1) % len(points)]
                    dist = self._point_to_line_distance(world_x, world_y, x1, y1, x2, y2)
                    if dist < search_radius * 2:
                        return ('polygon', i)
            
            elif obj['type'] == 'angle':
                vertex = obj['vertex']
                point1 = obj['point1']
                point2 = obj['point2']
                
                dist1 = self._point_to_line_distance(world_x, world_y, vertex[0], vertex[1], point1[0], point1[1])
                dist2 = self._point_to_line_distance(world_x, world_y, vertex[0], vertex[1], point2[0], point2[1])
                
                if min(dist1, dist2) < search_radius * 2:
                    return ('angle', i)
            
            elif obj['type'] == 'text':
                tx, ty = obj['pos']
                dist = math.sqrt((world_x - tx)**2 + (world_y - ty)**2)
                if dist < search_radius * 2:
                    return ('text', i)
        
        return None

    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    # ========== РИСОВАНИЕ ==========

    def draw_function(self, painter, function_data):
        """Рисует график функции"""
        if not function_data['visible']:
            return
            
        try:
            left, _ = self.screen_to_world(0, 0)
            right, _ = self.screen_to_world(self.width(), 0)
            
            margin = (right - left) * 0.05
            left -= margin
            right += margin
            
            x_points = np.linspace(left, right, 2000)
            func = function_data['func']
            
            try:
                y_points = func(x_points)
                
                screen_points = []
                for x, y in zip(x_points, y_points):
                    if np.isfinite(y):
                        screen_points.append(self.world_to_screen(x, float(y)))
                    else:
                        screen_points.append(None)
                
                if screen_points:
                    painter.setPen(QPen(function_data['color'], 2))
                    
                    segment_points = []
                    for point in screen_points:
                        if point is None:
                            if len(segment_points) > 1:
                                for i in range(len(segment_points) - 1):
                                    x1, y1 = segment_points[i]
                                    x2, y2 = segment_points[i + 1]
                                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                            segment_points = []
                        else:
                            segment_points.append(point)
                    
                    if len(segment_points) > 1:
                        for i in range(len(segment_points) - 1):
                            x1, y1 = segment_points[i]
                            x2, y2 = segment_points[i + 1]
                            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                            
            except (ValueError, ZeroDivisionError, TypeError, RuntimeWarning):
                pass
                
        except Exception as e:
            pass

    def get_grid_size(self):
        return self.base_grid_size * self.zoom_factor

    # ========== УПРАВЛЕНИЕ КАМЕРОЙ ==========

    def wheelEvent(self, event):
        """Зум колесиком мыши"""
        try:
            mouse_pos = event.position() if hasattr(event, 'position') else event.pos()
            old_pos = self.screen_to_world(mouse_pos.x(), mouse_pos.y())
            
            delta = event.angleDelta().y()
            old_zoom = self.zoom_factor
            
            if delta > 0:
                self.zoom_factor *= 1.2
            else:
                self.zoom_factor /= 1.2
                
            self.zoom_factor = max(self.min_zoom, min(self.max_zoom, self.zoom_factor))
            
            if old_zoom != self.zoom_factor:
                new_pos = self.screen_to_world(mouse_pos.x(), mouse_pos.y())
                world_dx = new_pos[0] - old_pos[0]
                world_dy = new_pos[1] - old_pos[1]
                screen_dx = world_dx * self.get_grid_size()
                screen_dy = world_dy * self.get_grid_size()
                
                self.offset_x -= screen_dx
                self.offset_y -= screen_dy
                
            self.update()
            
        except Exception as e:
            pass

    def draw_grid(self, painter):
        """Рисует сетку с осями координат"""
        if not self.show_grid:
            return

        painter.save()
        
        grid_size = self.get_grid_size()
        center_x = self.width() / 2 + self.offset_x
        center_y = self.height() / 2 + self.offset_y
        
        left, top = self.screen_to_world(0, 0)
        right, bottom = self.screen_to_world(self.width(), self.height())
        
        if self.zoom_factor < 0.1:
            step = 10
        elif self.zoom_factor < 0.5:
            step = 5
        elif self.zoom_factor < 1.0:
            step = 1
        elif self.zoom_factor < 2.0:
            step = 0.5
        else:
            step = 0.2
        
        start_x = math.floor(left / step) * step
        end_x = math.ceil(right / step) * step
        start_y = math.floor(bottom / step) * step
        end_y = math.ceil(top / step) * step
        
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        x = start_x
        while x <= end_x:
            screen_x, _ = self.world_to_screen(x, 0)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawLine(QPointF(screen_x, 0), QPointF(screen_x, self.height()))
            
            if abs(x) > step/2:
                painter.setPen(Qt.black)
                value = round(x, 3)
                text = str(int(value)) if value.is_integer() else f"{value}"
                rect = QRectF(screen_x + 5, center_y + 5, 50, 20)
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
            x += step
        
        y = start_y
        while y <= end_y:
            _, screen_y = self.world_to_screen(0, y)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawLine(QPointF(0, screen_y), QPointF(self.width(), screen_y))
            
            if abs(y) > step/2:
                painter.setPen(Qt.black)
                value = round(y, 3)
                text = str(int(value)) if value.is_integer() else f"{value}"
                rect = QRectF(center_x + 5, screen_y - 10, 50, 20)
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
            y += step
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(QPointF(0, center_y), QPointF(self.width(), center_y))
        painter.drawLine(QPointF(center_x, 0), QPointF(center_x, self.height()))
        
        painter.drawText(QPointF(self.width() - 20, center_y - 5), "X")
        painter.drawText(QPointF(center_x + 5, 15), "Y")
        
        painter.restore()

    def draw_object(self, painter, obj):
        """Рисует один геометрический объект"""
        if obj['type'] == 'point':
            x, y = self.world_to_screen(*obj['pos'])
            DrawingObjects.draw_point(painter, x, y)
            
        elif obj['type'] == 'line':
            x1, y1 = self.world_to_screen(*obj['points'][:2])
            x2, y2 = self.world_to_screen(*obj['points'][2:])
            
            painter.setPen(QPen(Qt.black, 2))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            if obj.get('infinite', False):
                pen = QPen(Qt.black, 1)
                pen.setDashPattern([5, 5])
                painter.setPen(pen)
                
                dx = x2 - x1
                dy = y2 - y1
                
                if abs(dx) > 0.1 or abs(dy) > 0.1:
                    length = math.sqrt(dx*dx + dy*dy)
                    norm_x = dx / length
                    norm_y = dy / length
                    
                    ext = max(self.width(), self.height()) * 3
                    
                    start_x = x1 - norm_x * ext
                    start_y = y1 - norm_y * ext
                    end_x = x2 + norm_x * ext
                    end_y = y2 + norm_y * ext
                    
                    painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))
            
        elif obj['type'] == 'circle':
            center_x, center_y = self.world_to_screen(*obj['center'])
            radius = obj['radius'] * self.get_grid_size()
            
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QBrush(Qt.NoBrush))
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)
            
            painter.setPen(QPen(Qt.red, 2))
            painter.setBrush(QBrush(Qt.red))
            painter.drawEllipse(QPointF(center_x, center_y), 3, 3)
        
        elif obj['type'] == 'polygon':
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QBrush(Qt.NoBrush))
            points_screen = [self.world_to_screen(*p) for p in obj['points']]
            for i in range(len(points_screen)):
                x1, y1 = points_screen[i]
                x2, y2 = points_screen[(i + 1) % len(points_screen)]
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        elif obj['type'] == 'angle':
            vertex = obj['vertex']
            point1 = obj['point1']
            point2 = obj['point2']
            
            vx, vy = self.world_to_screen(*vertex)
            p1x, p1y = self.world_to_screen(*point1)
            p2x, p2y = self.world_to_screen(*point2)
            
            painter.setPen(QPen(Qt.black, 2))
            painter.drawLine(QPointF(vx, vy), QPointF(p1x, p1y))
            painter.drawLine(QPointF(vx, vy), QPointF(p2x, p2y))
        
        elif obj['type'] == 'text':
            x, y = self.world_to_screen(*obj['pos'])
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", obj.get('size', 12)))
            painter.drawText(int(x), int(y), obj['text'])

    def draw_points(self, painter):
        """Рисует все добавленные точки"""
        for point in self.points:
            x, y = self.world_to_screen(*point['pos'])
            DrawingObjects.draw_point(painter, x, y)

    def draw_temp_construction_points(self, painter):
        """Рисует временные точки при построении"""
        if self.current_tool == 'angle' and self.angle_points:
            for point in self.angle_points:
                x, y = self.world_to_screen(*point)
                painter.setPen(QPen(QColor(0, 150, 255), 3))
                painter.setBrush(QBrush(QColor(0, 150, 255, 100)))
                painter.drawEllipse(QPointF(x, y), 6, 6)
        
        elif self.current_tool == 'polygon' and self.temp_object and self.temp_object.get('points'):
            for point in self.temp_object['points']:
                x, y = self.world_to_screen(*point)
                painter.setPen(QPen(QColor(0, 150, 255), 3))
                painter.setBrush(QBrush(QColor(0, 150, 255, 100)))
                painter.drawEllipse(QPointF(x, y), 6, 6)
            
            if len(self.temp_object['points']) > 1:
                painter.setPen(QPen(Qt.black, 1))
                for i in range(len(self.temp_object['points'])):
                    x1, y1 = self.world_to_screen(*self.temp_object['points'][i])
                    x2, y2 = self.world_to_screen(*self.temp_object['points'][(i + 1) % len(self.temp_object['points'])])
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def draw_snap_highlight(self, painter):
        """Рисует индикатор прилипания"""
        if self.snap_point:
            screen_x, screen_y = self.world_to_screen(self.snap_point['x'], self.snap_point['y'])
            
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setBrush(QBrush(QColor(255, 255, 0, 50)))
            painter.drawEllipse(QPointF(screen_x, screen_y), 10, 10)
            
            painter.setPen(QPen(QColor(255, 200, 0), 3))
            painter.drawPoint(QPointF(screen_x, screen_y))

    def draw_cursor_info(self, painter):
        """Рисует текущие координаты рядом с курсором"""
        painter.save()
        
        text = f"{i18n.get('coord_x')}{self.mouse_world_x:.2f}{i18n.get('coord_y')}{self.mouse_world_y:.2f}"
        
        font = QFont("Arial", 14)
        font.setBold(True)
        painter.setFont(font)
        
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()
        
        x = self.mouse_x + 20
        y = self.mouse_y - 20
        
        if x + text_width + 20 > self.width():
            x = self.width() - text_width - 25
        if y < 0:
            y = self.mouse_y + 30
        if y + text_height + 10 > self.height():
            y = self.height() - text_height - 15
            
        rect = QRectF(x, y, text_width + 16, text_height + 8)
        
        painter.fillRect(rect, QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.setBrush(QBrush())
        painter.drawRect(rect)
        
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawText(rect, Qt.AlignCenter, text)
        
        painter.restore()

    def paintEvent(self, event):
        """Главная функция отрисовки"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.show_grid:
            self.draw_grid(painter)

        for func_data in self.functions.values():
            self.draw_function(painter, func_data)

        for obj in self.objects:
            self.draw_object(painter, obj)

        if self.temp_object and self.temp_object['type'] not in ['polygon', 'angle']:
            self.draw_object(painter, self.temp_object)

        self.draw_points(painter)
        self.draw_temp_construction_points(painter)
        self.draw_snap_highlight(painter)
        self.draw_cursor_info(painter)

    # ========== ДИАЛОГИ ВВОДА ==========

    def show_angle_input_dialog(self):
        text, ok = QInputDialog.getDouble(
            self, 
            i18n.get('dialog_angle_title'), 
            i18n.get('dialog_angle_prompt'),
            90, -360, 360, 1
        )
        return text if ok else None

    def show_text_input_dialog(self):
        text, ok = QInputDialog.getText(
            self, 
            i18n.get('dialog_text_title'), 
            i18n.get('dialog_text_prompt')
        )
        return text if ok else None

    # ========== СОБЫТИЯ МЫШИ ==========

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши"""
        print(f"{i18n.get('msg_click')}({event.pos().x()}, {event.pos().y()})")
        
        if event.button() == Qt.RightButton:
            obj_info = self.find_object_at_point(self.mouse_world_x, self.mouse_world_y)
            if obj_info:
                obj_type, obj_index = obj_info
                if obj_type == 'point':
                    self.points.pop(obj_index)
                else:
                    self.objects.pop(obj_index)
                self.update()
        
        elif event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        
        elif event.button() == Qt.LeftButton:
            self._handle_left_click(event)

    def _handle_left_click(self, event):
        """Обработка левого клика в зависимости от инструмента"""
        
        if self.current_tool == 'point':
            snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
            world_pos = (snap['x'], snap['y']) if snap else (self.mouse_world_x, self.mouse_world_y)
            self.points.append({'pos': world_pos})
            self.update()
        
        elif self.current_tool == 'line':
            if self.start_pos is None:
                self.start_pos = event.pos()
            else:
                snap1 = self.find_snap_point(*self.screen_to_world(self.start_pos.x(), self.start_pos.y()))
                snap2 = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
                
                x1, y1 = (snap1['x'], snap1['y']) if snap1 else self.screen_to_world(self.start_pos.x(), self.start_pos.y())
                x2, y2 = (snap2['x'], snap2['y']) if snap2 else (self.mouse_world_x, self.mouse_world_y)
                
                is_connected = self._check_line_connection(x1, y1, x2, y2)
                
                self.objects.append({
                    'type': 'line',
                    'points': (x1, y1, x2, y2),
                    'infinite': not is_connected
                })
                
                self.start_pos = None
                self.temp_object = None
                self.update()
        
        elif self.current_tool == 'circle':
            if self.start_pos is None:
                snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
                self.start_pos = (snap['x'], snap['y']) if snap else self.screen_to_world(event.pos().x(), event.pos().y())
            else:
                center = self.start_pos
                snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
                current = (snap['x'], snap['y']) if snap else self.screen_to_world(event.pos().x(), event.pos().y())
                
                radius = math.sqrt((current[0] - center[0])**2 + (current[1] - center[1])**2)
                
                self.objects.append({
                    'type': 'circle',
                    'center': center,
                    'radius': radius
                })
                
                self.start_pos = None
                self.temp_object = None
                self.update()
        
        elif self.current_tool == 'angle':
            if len(self.angle_points) < 3:
                snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
                self.angle_points.append((snap['x'], snap['y']) if snap else (self.mouse_world_x, self.mouse_world_y))
                self.update()
            
            if len(self.angle_points) == 3:
                self._finalize_angle()
        
        elif self.current_tool == 'polygon':
            if self.temp_object is None:
                self.temp_object = {'type': 'polygon', 'points': []}
            
            snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
            world_pos = (snap['x'], snap['y']) if snap else self.screen_to_world(event.pos().x(), event.pos().y())
            
            self.temp_object['points'].append(world_pos)
            self.update()
        
        elif self.current_tool == 'text':
            text = self.show_text_input_dialog()
            if text:
                self.objects.append({
                    'type': 'text',
                    'pos': (self.mouse_world_x, self.mouse_world_y),
                    'text': text,
                    'size': 12
                })
                self.update()

    def _check_line_connection(self, x1, y1, x2, y2):
        """Проверяет соединена ли линия с другими объектами"""
        snap_dist = self.snap_radius / self.get_grid_size()
        
        for point in self.points:
            px, py = point['pos']
            d1 = math.sqrt((x1 - px)**2 + (y1 - py)**2)
            d2 = math.sqrt((x2 - px)**2 + (y2 - py)**2)
            if d1 < snap_dist or d2 < snap_dist:
                return True
        
        for obj in self.objects:
            if obj['type'] == 'circle':
                cx, cy = obj['center']
                d1 = math.sqrt((x1 - cx)**2 + (y1 - cy)**2)
                d2 = math.sqrt((x2 - cx)**2 + (y2 - cy)**2)
                if d1 < snap_dist or d2 < snap_dist:
                    return True
        
        return False

    def _finalize_angle(self):
        """Завершает построение угла"""
        angle_value = self.show_angle_input_dialog()
        
        if angle_value is not None:
            point1 = self.angle_points[0]
            vertex = self.angle_points[1]
            point3 = self.angle_points[2]
            
            v1x = point1[0] - vertex[0]
            v1y = point1[1] - vertex[1]
            len1 = math.sqrt(v1x**2 + v1y**2)
            
            v3x = point3[0] - vertex[0]
            v3y = point3[1] - vertex[1]
            len3 = math.sqrt(v3x**2 + v3y**2)
            
            if len1 > 0.001:
                angle1_rad = math.atan2(v1y, v1x)
                angle3_rad = math.atan2(v3y, v3x)
                angle_diff_rad = angle3_rad - angle1_rad
                
                while angle_diff_rad > math.pi:
                    angle_diff_rad -= 2 * math.pi
                while angle_diff_rad < -math.pi:
                    angle_diff_rad += 2 * math.pi
                
                if angle_diff_rad >= 0:
                    angle2_rad = angle1_rad + math.radians(angle_value)
                else:
                    angle2_rad = angle1_rad - math.radians(angle_value)
                
                point2 = (
                    vertex[0] + len1 * math.cos(angle2_rad),
                    vertex[1] + len1 * math.sin(angle2_rad)
                )
                
                self.objects.append({
                    'type': 'angle',
                    'vertex': vertex,
                    'point1': point1,
                    'point2': point2,
                    'angle': angle_value
                })
                
                for p in [point1, vertex, point2]:
                    self.points.append({'pos': p})
                
                self.angle_points = []
                self.update()
        else:
            self.angle_points = []

    def mouseReleaseEvent(self, event):
        """Отпускание кнопки мыши"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            self.last_pan_pos = None
        
        elif event.button() == Qt.RightButton:
            if self.current_tool == 'polygon' and self.temp_object and len(self.temp_object['points']) > 2:
                snap = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
                world_pos = (snap['x'], snap['y']) if snap else self.screen_to_world(event.pos().x(), event.pos().y())
                
                first_point = self.temp_object['points'][0]
                snap_dist = self.snap_radius / self.get_grid_size()
                dist_to_first = math.sqrt((world_pos[0] - first_point[0])**2 + (world_pos[1] - first_point[1])**2)
                
                if dist_to_first < snap_dist:
                    for point_pos in self.temp_object['points']:
                        self.points.append({'pos': point_pos})
                    
                    self.objects.append(self.temp_object)
                    self.temp_object = None
                    self.update()

    def mouseMoveEvent(self, event):
        """Движение мыши"""
        self.mouse_x = event.pos().x()
        self.mouse_y = event.pos().y()
        self.mouse_world_x, self.mouse_world_y = self.screen_to_world(self.mouse_x, self.mouse_y)
        
        self.snap_point = self.find_snap_point(self.mouse_world_x, self.mouse_world_y)
        
        if self.is_panning and self.last_pan_pos:
            delta = event.pos() - self.last_pan_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_pan_pos = event.pos()
            self.update()
        
        elif self.start_pos and self.current_tool:
            if self.current_tool == 'line':
                self.temp_object = {
                    'type': 'line',
                    'points': (*self.screen_to_world(self.start_pos.x(), self.start_pos.y()),
                              *self.screen_to_world(event.pos().x(), event.pos().y())),
                    'infinite': False
                }
            elif self.current_tool == 'circle':
                center = self.start_pos
                current = self.screen_to_world(event.pos().x(), event.pos().y())
                radius = ((current[0] - center[0])**2 + (current[1] - center[1])**2)**0.5
                self.temp_object = {
                    'type': 'circle',
                    'center': center,
                    'radius': radius
                }
            self.update()
        else:
            self.update()

    def keyPressEvent(self, event):
        """Нажатие клавиши"""
        if event.key() == Qt.Key_Escape:
            if self.current_tool == 'polygon' and self.temp_object and len(self.temp_object['points']) > 2:
                for point_pos in self.temp_object['points']:
                    self.points.append({'pos': point_pos})
                
                self.objects.append(self.temp_object)
                self.temp_object = None
                self.update()
            
            elif self.current_tool == 'angle' and self.angle_points:
                self.angle_points = []
                self.update()
        
        elif event.key() == Qt.Key_Space:
            self.setCursor(Qt.OpenHandCursor)
        
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Отпускание клавиши"""
        if event.key() == Qt.Key_Space:
            self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)

    # ========== ПРЕОБРАЗОВАНИЕ КООРДИНАТ ==========

    def world_to_screen(self, x, y):
        """Мировые координаты → экранные пиксели"""
        center_x = self.width() / 2 + self.offset_x
        center_y = self.height() / 2 + self.offset_y
        screen_x = center_x + x * self.get_grid_size()
        screen_y = center_y - y * self.get_grid_size()
        return screen_x, screen_y

    def screen_to_world(self, screen_x, screen_y):
        """Экранные пиксели → мировые координаты"""
        center_x = self.width() / 2 + self.offset_x
        center_y = self.height() / 2 + self.offset_y
        grid_size = self.get_grid_size()
        x = (screen_x - center_x) / grid_size
        y = (center_y - screen_y) / grid_size
        return x, y


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    language_changed = pyqtSignal(str)
    DATA_DIR = Path("projects")
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(i18n.get('window_title'))
        self.setGeometry(100, 100, 1200, 800)
        
        self.DATA_DIR.mkdir(exist_ok=True)
        
        # Главный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Верхняя панель с языком
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопка переключения языка
        self.language_btn = QPushButton(i18n.get('toolbar_language'))
        self.language_btn.clicked.connect(self._toggle_language)
        self.language_btn.setMaximumWidth(80)
        top_layout.addStretch()
        top_layout.addWidget(self.language_btn)
        
        language_container = QWidget()
        language_container.setLayout(top_layout)
        language_container.setMaximumHeight(40)
        main_layout.addWidget(language_container)
        
        # Панель инструментов
        self.toolbar = HoverToolbar(self)
        self.toolbar.grid_toggled.connect(self.toggle_grid)
        self.toolbar.function_added.connect(self.add_function)
        self.toolbar.function_deleted.connect(self.delete_function)
        self.toolbar.function_toggled.connect(self.toggle_function)
        self.toolbar.tool_selected.connect(self.on_tool_selected)
        self.toolbar.save_requested.connect(self.on_save_requested)
        self.toolbar.load_requested.connect(self.on_load_requested)
        main_layout.addWidget(self.toolbar)
        
        # Холст
        self.canvas = DrawingCanvas()
        main_layout.addWidget(self.canvas)

    def _toggle_language(self):
        """Переключить язык"""
        current = i18n.get_current_language()
        new_lang = 'ru' if current == 'en' else 'en'
        self._set_language(new_lang)

    def _set_language(self, language: str):
        """Установить язык и обновить UI"""
        if i18n.set_language(language):
            print(f"DEBUG: i18n language set to {language}")
            
            # Обновляем кнопку
            self.language_btn.setText(i18n.get('toolbar_language'))
            print(f"DEBUG: Language button updated")
            
            # Обновляем заголовок окна
            self.setWindowTitle(i18n.get('window_title'))
            print(f"DEBUG: Window title updated")
            
            # Обновляем панель инструментов
            print(f"DEBUG: Calling toolbar.update_language()")
            self.toolbar.update_language()
            print(f"DEBUG: toolbar.update_language() completed")
            
            print(f"✓ Language changed to: {language}")

    def toggle_grid(self, show):
        self.canvas.show_grid = show
        self.canvas.update()

    def add_function(self, function_text):
        self.canvas.add_function(function_text)

    def delete_function(self, func_index):
        self.canvas.delete_function(func_index)

    def toggle_function(self, func_index, visible):
        self.canvas.toggle_function(func_index, visible)

    def on_tool_selected(self, tool_name):
        print(f"{i18n.get('msg_tool_changed')}{tool_name}")
        self.canvas.set_current_tool(tool_name)

    def keyPressEvent(self, event):
        self.canvas.keyPressEvent(event)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.canvas.keyReleaseEvent(event)
        super().keyReleaseEvent(event)

    # ========== СОХРАНЕНИЕ И ЗАГРУЗКА (JSON) ==========

    def on_save_requested(self):
        """Сохраняет проект в JSON"""
        filename, ok = QInputDialog.getText(
            self, 
            i18n.get('dialog_save_title'), 
            i18n.get('dialog_save_prompt')
        )
        
        if ok and filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = self.DATA_DIR / filename
            
            try:
                data = self._serialize_project()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"{i18n.get('msg_saved')}{filepath}")
                
            except Exception as e:
                print(f"{i18n.get('msg_error_save')}{e}")

    def on_load_requested(self):
        """Загружает проект из JSON"""
        filename, ok = QInputDialog.getText(
            self, 
            i18n.get('dialog_load_title'), 
            i18n.get('dialog_load_prompt')
        )
        
        if ok and filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = self.DATA_DIR / filename
            
            try:
                if not filepath.exists():
                    print(f"{i18n.get('msg_file_not_found')}{filepath}")
                    return
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._deserialize_project(data)
                print(f"{i18n.get('msg_loaded')}{filepath}")
                
            except Exception as e:
                print(f"{i18n.get('msg_error_load')}{e}")

    def _serialize_project(self) -> dict:
        """Преобразует рабочую область в JSON-совместимый словарь"""
        data = {
            'version': '1.0',
            'camera': {
                'zoom': self.canvas.zoom_factor,
                'offset_x': self.canvas.offset_x,
                'offset_y': self.canvas.offset_y,
            },
            'functions': {},
            'objects': [],
            'points': []
        }
        
        # Функции
        for idx, func_data in self.canvas.functions.items():
            data['functions'][str(idx)] = {
                'text': func_data['text'],
                'visible': func_data['visible']
            }
        
        # Объекты
        for obj in self.canvas.objects:
            if obj['type'] == 'point':
                data['objects'].append({
                    'type': 'point',
                    'pos': list(obj['pos'])
                })
            elif obj['type'] == 'line':
                data['objects'].append({
                    'type': 'line',
                    'points': list(obj['points']),
                    'infinite': obj.get('infinite', False)
                })
            elif obj['type'] == 'circle':
                data['objects'].append({
                    'type': 'circle',
                    'center': list(obj['center']),
                    'radius': obj['radius']
                })
            elif obj['type'] == 'polygon':
                data['objects'].append({
                    'type': 'polygon',
                    'points': [list(p) for p in obj['points']]
                })
            elif obj['type'] == 'angle':
                data['objects'].append({
                    'type': 'angle',
                    'vertex': list(obj['vertex']),
                    'point1': list(obj['point1']),
                    'point2': list(obj['point2']),
                    'angle': obj['angle']
                })
            elif obj['type'] == 'text':
                data['objects'].append({
                    'type': 'text',
                    'pos': list(obj['pos']),
                    'text': obj['text'],
                    'size': obj.get('size', 12)
                })
        
        # Точки
        for point in self.canvas.points:
            data['points'].append({
                'pos': list(point['pos'])
            })
        
        return data

    def _deserialize_project(self, data: dict):
        """Восстанавливает рабочую область из JSON"""
        # Очищаем холст
        self.canvas.objects = []
        self.canvas.points = []
        self.canvas.functions = {}
        self.canvas.angle_points = []
        self.canvas.temp_object = None
        
        # Восстанавливаем камеру
        if 'camera' in data:
            camera = data['camera']
            self.canvas.zoom_factor = camera.get('zoom', 1.0)
            self.canvas.offset_x = camera.get('offset_x', 0.0)
            self.canvas.offset_y = camera.get('offset_y', 0.0)
        
        # Функции
        for idx_str, func_data in data.get('functions', {}).items():
            idx = int(idx_str)
            self.canvas._process_function(func_data['text'], idx)
            if not func_data.get('visible', True):
                self.canvas.functions[idx]['visible'] = False
        
        # Объекты
        for obj_data in data.get('objects', []):
            obj_type = obj_data['type']
            
            if obj_type == 'point':
                self.canvas.objects.append({
                    'type': 'point',
                    'pos': tuple(obj_data['pos'])
                })
            elif obj_type == 'line':
                self.canvas.objects.append({
                    'type': 'line',
                    'points': tuple(obj_data['points']),
                    'infinite': obj_data.get('infinite', False)
                })
            elif obj_type == 'circle':
                self.canvas.objects.append({
                    'type': 'circle',
                    'center': tuple(obj_data['center']),
                    'radius': obj_data['radius']
                })
            elif obj_type == 'polygon':
                self.canvas.objects.append({
                    'type': 'polygon',
                    'points': [tuple(p) for p in obj_data['points']]
                })
            elif obj_type == 'angle':
                self.canvas.objects.append({
                    'type': 'angle',
                    'vertex': tuple(obj_data['vertex']),
                    'point1': tuple(obj_data['point1']),
                    'point2': tuple(obj_data['point2']),
                    'angle': obj_data['angle']
                })
            elif obj_type == 'text':
                self.canvas.objects.append({
                    'type': 'text',
                    'pos': tuple(obj_data['pos']),
                    'text': obj_data['text'],
                    'size': obj_data.get('size', 12)
                })
        
        # Точки
        for point_data in data.get('points', []):
            self.canvas.points.append({
                'pos': tuple(point_data['pos'])
            })
        
        self.canvas.update()

    def closeEvent(self, event):
        """Завершение приложения"""
        try:
            if hasattr(self, 'canvas'):
                self.canvas.deleteLater()
            if hasattr(self, 'toolbar'):
                self.toolbar.deleteLater()
            event.accept()
        except Exception as e:
            print(f"✗ Error closing: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton)
    
    window = MainWindow()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except SystemExit:
        pass
    except Exception as e:
        print(f"✗ Error: {e}")