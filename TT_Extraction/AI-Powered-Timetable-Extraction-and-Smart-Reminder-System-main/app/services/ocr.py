"""
OCR service for timetable extraction - No Hardcoding
"""

import cv2
import re
from paddleocr import PaddleOCR
from typing import List, Dict
import os

class OCRService:
    def __init__(self):
        """Initialize PaddleOCR"""
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            show_log=False
        )
    
    def preprocess_image(self, image_path: str):
        """Simple preprocessing"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_courses(self, image_path: str) -> Dict[str, Dict]:
        """Extract course details with slot information"""
        processed = self.preprocess_image(image_path)
        result = self.ocr.ocr(processed, cls=True)
        
        if not result or not result[0]:
            return {}
        
        courses = {}
        
        for line in result[0]:
            text = line[1][0].strip()
            
            # Look for course codes
            code_match = re.search(r'(CSE|MAT|STS|EXC)\s*(\d{4})', text)
            if code_match:
                code = f"{code_match.group(1)}{code_match.group(2)}"
                
                # Extract slot codes from the same line
                # Look for patterns like A2, T2A, etc.
                slot_matches = re.findall(r'\b([A-Z][0-9]{1,2}[A-Z]?)\b', text)
                
                # Also look for patterns with plus signs like A2+T2A
                plus_pattern = re.findall(r'([A-Z0-9]+(?:\+[A-Z0-9]+)+)', text)
                if plus_pattern:
                    for pattern in plus_pattern:
                        slots = pattern.split('+')
                        slot_matches.extend(slots)
                
                # Store all unique slots
                unique_slots = list(set(slot_matches))
                
                if code not in courses:
                    courses[code] = {
                        'code': code,
                        'slots': unique_slots,
                        'raw_text': text
                    }
        
        return courses
    
    def extract_schedule(self, image_path: str) -> List[List[str]]:
        """Extract schedule grid"""
        processed = self.preprocess_image(image_path)
        result = self.ocr.ocr(processed, cls=True)
        
        if not result or not result[0]:
            return []
        
        # Group text by position
        elements = []
        for line in result[0]:
            bbox = line[0]
            text = line[1][0].strip()
            if text:
                center_x = sum(p[0] for p in bbox) / 4
                center_y = sum(p[1] for p in bbox) / 4
                elements.append({
                    'text': text,
                    'x': center_x,
                    'y': center_y
                })
        
        # Group by y-coordinate
        y_threshold = 30
        rows = {}
        for elem in elements:
            y = elem['y']
            found = False
            for row_y in rows.keys():
                if abs(y - row_y) < y_threshold:
                    rows[row_y].append(elem)
                    found = True
                    break
            if not found:
                rows[y] = [elem]
        
        sorted_rows = sorted(rows.items())
        
        # Day mapping
        day_map = {
            'TUE': 'Tuesday', 'WED': 'Wednesday', 'THU': 'Thursday',
            'FRI': 'Friday', 'SAT': 'Saturday', 'MON': 'Monday'
        }
        
        raw_data = []
        current_day = None
        current_type = None
        
        for y, row_elems in sorted_rows:
            row_elems.sort(key=lambda e: e['x'])
            row_texts = [e['text'] for e in row_elems]
            
            # Detect day
            for text in row_texts[:3]:
                if text in day_map:
                    current_day = day_map[text]
                    break
            
            # Detect theory/lab
            if 'THEORY' in row_texts:
                current_type = 'THEORY'
                continue
            elif 'LAB' in row_texts:
                current_type = 'LAB'
                continue
            
            # If we have a day and type, collect slot codes
            if current_day and current_type:
                row = [current_day, current_type]
                
                for text in row_texts:
                    # Skip known headers
                    if text in day_map or text in ['THEORY', 'LAB', 'End', 'Start', 'Lunch']:
                        continue
                    
                    # Clean the text - extract only the slot/course code
                    cleaned = re.sub(r'-[A-Z0-9\-]+$', '', text)
                    cleaned = re.sub(r'\.$', '', cleaned)
                    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned)
                    
                    if cleaned and len(cleaned) >= 2:
                        row.append(cleaned)
                        row.append("")  # Faculty placeholder
                
                if len(row) > 2:
                    raw_data.append(row)
        
        return raw_data
    
    def build_slot_mapping(self, courses: Dict) -> Dict[str, str]:
        """Build mapping from slot codes to course codes using extracted data"""
        slot_to_course = {}
        
        for code, course in courses.items():
            for slot in course.get('slots', []):
                if slot:
                    slot_to_course[slot] = code
        
        return slot_to_course
    
    def map_courses_to_slots(self, raw_data: List[List[str]], slot_mapping: Dict[str, str]) -> List[List[str]]:
        """Replace slot codes with actual course codes"""
        updated_data = []
        
        for row in raw_data:
            new_row = row.copy()
            
            for i in range(2, len(row), 2):
                value = row[i]
                if value and value != "-":
                    # Check if value is a slot code in our mapping
                    if value in slot_mapping:
                        new_row[i] = slot_mapping[value]
                    # Also check if the value contains a slot code
                    else:
                        for slot, course in slot_mapping.items():
                            if slot in value:
                                new_row[i] = course
                                break
            
            updated_data.append(new_row)
        
        return updated_data
    
    def process_timetable(self, course_image_path: str, schedule_image_path: str) -> List[List[str]]:
        """Main processing pipeline"""
        # Extract courses with their slot info
        courses = self.extract_courses(course_image_path)
        
        # Extract schedule grid
        raw_data = self.extract_schedule(schedule_image_path)
        
        # Build mapping from slots to courses
        slot_mapping = self.build_slot_mapping(courses)
        
        # Apply mapping
        if slot_mapping:
            raw_data = self.map_courses_to_slots(raw_data, slot_mapping)
        
        return raw_data