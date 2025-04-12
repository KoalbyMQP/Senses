import zmq
import time
import pygame
import math
import sys


WIDTH, HEIGHT = 800, 800
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
DARK_GRAY = (80, 80, 80)
BACKGROUND = (245, 245, 240)

STEPS_PER_REVOLUTION = 200
DEGREES_PER_INPUT = 50 
MAX_INPUT = 11         

class ConfirmationListener:
    def __init__(self, host_ip):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.bind(f"tcp://*:5562")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Gripper Status Visualizer")
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 16)
        self.tiny_font = pygame.font.SysFont('Arial', 12)
        self.clock = pygame.time.Clock()

        self.current_position = 0  
        self.target_position = 0   
        self.angle = 0.0           
        self.input_value = 0       
        self.is_moving = False     
        self.last_status_msg = "Waiting for first confirmation..."
        self.last_total_latency = 0.0
        self.last_current_gripper = 0
        self.last_previous_gripper = 0

        print(f"\n===== Confirmation Listener & Visualizer =====")
        print(f"Started on {host_ip}:5562")
        print(f"Waiting for gripper swap confirmation messages...")
        print(f"Pygame window opened for visualization.")
        print(f"==========================================\n")

    def calculate_steps(self, input_val):
        """Calculate motor steps from input value (0-11)"""
        input_val = max(0, min(MAX_INPUT, input_val))
        return round(input_val * DEGREES_PER_INPUT * (STEPS_PER_REVOLUTION / 360.0))

    def draw_compass(self):
        """Draw the compass visualization based on the current angle and input value"""
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        outer_radius = 300
        inner_radius = 230
        angle_offset = 180

        adjusted_angle = -self.angle

        temp_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        temp_surface.fill((0, 0, 0, 0))

        pygame.draw.circle(temp_surface, WHITE, (center_x, center_y), outer_radius)
        pygame.draw.circle(temp_surface, DARK_GRAY, (center_x, center_y), outer_radius, 1)
        pygame.draw.circle(temp_surface, DARK_GRAY, (center_x, center_y), inner_radius, 1)
        pygame.draw.line(temp_surface, BLACK, (center_x - 150, center_y), (center_x + 150, center_y), 1)
        pygame.draw.line(temp_surface, BLACK, (center_x, center_y - 150), (center_x, center_y + 150), 1)

        for i in range(72):
            compass_angle_deg = i * 5
            display_angle_deg = (compass_angle_deg + angle_offset) % 360
            angle_rad = math.radians(display_angle_deg)

            if i % 6 == 0:
                inner_tick = inner_radius
                outer_tick = outer_radius
                text_radius = inner_radius - 25
                text_x = center_x + math.sin(angle_rad) * text_radius
                text_y = center_y - math.cos(angle_rad) * text_radius
                degree_text = self.tiny_font.render(f"{compass_angle_deg}", True, DARK_GRAY)
                text_rect = degree_text.get_rect(center=(text_x, text_y))
                temp_surface.blit(degree_text, text_rect)
            elif i % 2 == 0:
                inner_tick = inner_radius + 5
                outer_tick = outer_radius
                text_radius = inner_radius - 15
                text_x = center_x + math.sin(angle_rad) * text_radius
                text_y = center_y - math.cos(angle_rad) * text_radius
                small_degree_text = pygame.font.SysFont('Arial', 10).render(f"{compass_angle_deg}", True, DARK_GRAY)
                text_rect = small_degree_text.get_rect(center=(text_x, text_y))
                temp_surface.blit(small_degree_text, text_rect)
            else:
                inner_tick = inner_radius + 15
                outer_tick = outer_radius

            inner_point = (center_x + math.sin(angle_rad) * inner_tick, center_y - math.cos(angle_rad) * inner_tick)
            outer_point = (center_x + math.sin(angle_rad) * outer_tick, center_y - math.cos(angle_rad) * outer_tick)
            pygame.draw.line(temp_surface, DARK_GRAY, inner_point, outer_point, 1)

        for i in range(360):
            if i % 5 == 0: continue
            compass_angle_deg = i
            display_angle_deg = (compass_angle_deg + angle_offset) % 360
            angle_rad = math.radians(display_angle_deg)
            inner_tick = inner_radius + 25
            outer_tick = outer_radius - 5
            inner_point = (center_x + math.sin(angle_rad) * inner_tick, center_y - math.cos(angle_rad) * inner_tick)
            outer_point = (center_x + math.sin(angle_rad) * outer_tick, center_y - math.cos(angle_rad) * outer_tick)
            pygame.draw.line(temp_surface, (150, 150, 150), inner_point, outer_point, 1)

        directions = [("S", 0), ("W", 90), ("N", 180), ("E", 270)]
        for direction, deg in directions:
            display_angle_deg = (deg + angle_offset) % 360
            angle_rad = math.radians(display_angle_deg)
            text_x = center_x + math.sin(angle_rad) * (inner_radius - 60)
            text_y = center_y - math.cos(angle_rad) * (inner_radius - 60)
            direction_text = self.font.render(direction, True, BLACK)
            text_rect = direction_text.get_rect(center=(text_x, text_y))
            temp_surface.blit(direction_text, text_rect)

        center_text = self.small_font.render("GRIPPER STATION", True, BLACK)
        center_text_rect = center_text.get_rect(center=(center_x, center_y + 20))
        temp_surface.blit(center_text, center_text_rect)

        input_degrees = (self.input_value * DEGREES_PER_INPUT) % 360
        input_display_angle = (input_degrees + angle_offset) % 360
        input_rad = math.radians(input_display_angle)
        marker_x = center_x + math.sin(input_rad) * (outer_radius - 15)
        marker_y = center_y - math.cos(input_rad) * (outer_radius - 15)
        marker_size = 8

        tip_x = center_x + math.sin(input_rad) * outer_radius
        tip_y = center_y - math.cos(input_rad) * outer_radius
        base_angle1 = input_rad + math.radians(90)
        base_angle2 = input_rad - math.radians(90)
        base_x1 = marker_x + math.sin(base_angle1) * marker_size
        base_y1 = marker_y - math.cos(base_angle1) * marker_size
        base_x2 = marker_x + math.sin(base_angle2) * marker_size
        base_y2 = marker_y - math.cos(base_angle2) * marker_size
        pygame.draw.polygon(temp_surface, BLUE, [(tip_x, tip_y), (base_x1, base_y1), (base_x2, base_y2)])

        rotated_surface = pygame.transform.rotate(temp_surface, adjusted_angle)
        rotated_rect = rotated_surface.get_rect(center=(center_x, center_y))
        self.screen.blit(rotated_surface, rotated_rect.topleft)

        needle_length = inner_radius - 40
        fixed_angle_rad = math.radians(180)
        end_x = center_x + math.sin(fixed_angle_rad) * needle_length
        end_y = center_y - math.cos(fixed_angle_rad) * needle_length
        pygame.draw.line(self.screen, RED, (center_x, center_y), (end_x, end_y), 3)

        arrowhead_size = 10
        arrow_angle1 = fixed_angle_rad + math.radians(150)
        arrow_angle2 = fixed_angle_rad - math.radians(150)
        arrow_x1 = end_x + math.sin(arrow_angle1) * arrowhead_size
        arrow_y1 = end_y - math.cos(arrow_angle1) * arrowhead_size
        arrow_x2 = end_x + math.sin(arrow_angle2) * arrowhead_size
        arrow_y2 = end_y - math.cos(arrow_angle2) * arrowhead_size
        pygame.draw.polygon(self.screen, RED, [(end_x, end_y), (arrow_x1, arrow_y1), (arrow_x2, arrow_y2)])


    def draw_info_panel(self):
        """Draw information panel with position details"""
        panel_x, panel_y = 10, 10
        panel_width = 280
        panel_height = 210
        pygame.draw.rect(self.screen, WHITE, (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, BLACK, (panel_x, panel_y, panel_width, panel_height), 1)

        pos_text = self.font.render(f"Target Position: {self.input_value}", True, BLUE)
        self.screen.blit(pos_text, (panel_x + 10, panel_y + 10))

        curr_gripper_text = self.small_font.render(f"Current Gripper Cmd: {self.last_current_gripper}", True, BLACK)
        self.screen.blit(curr_gripper_text, (panel_x + 10, panel_y + 40))
        prev_gripper_text = self.small_font.render(f"Previous Gripper Cmd: {self.last_previous_gripper}", True, BLACK)
        self.screen.blit(prev_gripper_text, (panel_x + 10, panel_y + 65))

        steps_text = self.font.render(f"Motor Steps: {self.target_position}", True, BLACK)
        self.screen.blit(steps_text, (panel_x + 10, panel_y + 95))

        angle_text = self.font.render(f"Current Angle: {self.angle:.1f}°", True, BLACK)
        self.screen.blit(angle_text, (panel_x + 10, panel_y + 125))

        status_text = self.small_font.render(f"Status: {self.last_status_msg}", True, BLACK)
        self.screen.blit(status_text, (panel_x + 10, panel_y + 155))

        latency_text = self.small_font.render(f"Total Latency: {self.last_total_latency*1000:.1f}ms", True, BLACK)
        self.screen.blit(latency_text, (panel_x + 10, panel_y + 180))


    def start_listening(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            try:
                message = self.socket.recv_string(flags=zmq.NOBLOCK)
                parts = message.split('|')
                if len(parts) == 8:
                    current_gripper_str, previous_gripper_str, voice_sent_str, host_forwarded_str, \
                    client_received_str, processing_time_str, client_sent_str, status = parts

                    try:
                        current_gripper = int(float(current_gripper_str))
                        previous_gripper = int(float(previous_gripper_str))
                        voice_sent = float(voice_sent_str)
                        client_sent = float(client_sent_str)

                        self.last_status_msg = {
                            "success": "Swap successful",
                            "already_active": "Gripper already active"
                        }.get(status, "Unknown status")
                        self.last_total_latency = client_sent - voice_sent
                        self.last_current_gripper = current_gripper
                        self.last_previous_gripper = previous_gripper

                        self.input_value = max(0, min(MAX_INPUT, current_gripper))

                        self.target_position = self.calculate_steps(self.input_value)

                        self.angle = (self.target_position / STEPS_PER_REVOLUTION) * 360.0
                        self.angle %= 360

                        print(f"Received confirmation: Gripper {previous_gripper} -> {current_gripper}. Status: {status}. Angle: {self.angle:.1f}°")

                    except ValueError as ve:
                        print(f"Error parsing message parts: {ve} - Message: {message}")

            except zmq.Again:
                pass
            except Exception as e:
                print(f"Listener error: {e}")

            self.screen.fill(BACKGROUND)
            self.draw_compass()
            self.draw_info_panel()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        print("Pygame visualizer closed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python confirmationListener.py <host_ip>")
        exit(1)

    listener = ConfirmationListener(sys.argv[1])
    listener.start_listening() 