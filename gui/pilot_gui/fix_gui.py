#!/usr/bin/env python3
"""
pilot_gui.py의 중괄호 충돌 문제를 해결하는 스크립트
"""

def fix_pilot_gui():
    # 파일 읽기
    with open('pilot_gui.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 수정된 라인들
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # base_style 정의 부분을 찾아서 건너뛰기
        if 'base_style = """QLabel {' in line:
            # base_style 정의 전체를 건너뛰고 if 문까지 찾기
            while i < len(lines) and 'if ' not in lines[i]:
                i += 1
            
            # 이제 if 문부터 처리
            if i < len(lines):
                if_line = lines[i].strip()
                
                # 조류 위험도 부분
                if 'risk_level ==' in if_line:
                    new_lines.append('            # 색상 설정 (원래 UI 스타일 유지하면서 색상만 변경)\n')
                    new_lines.append('            if risk_level == "BR_HIGH":\n')
                    new_lines.append('                border_color = "#cc0000"\n')
                    new_lines.append('                text_color = "#ff4444"\n')
                    new_lines.append('            elif risk_level == "BR_MEDIUM":\n')
                    new_lines.append('                border_color = "#cc8800"\n')
                    new_lines.append('                text_color = "#ffaa00"\n')
                    new_lines.append('            else:\n')
                    new_lines.append('                border_color = "#006600"\n')
                    new_lines.append('                text_color = "#00ff00"\n')
                    new_lines.append('            \n')
                    new_lines.append('            style = f"""QLabel {{\n')
                    new_lines.append('                font-weight: bold;\n')
                    new_lines.append('                background-color: #000800;\n')
                    new_lines.append('                border: 2px solid {border_color};\n')
                    new_lines.append('                border-radius: 6px;\n')
                    new_lines.append('                padding: 8px;\n')
                    new_lines.append('                font-family: "Courier New", monospace;\n')
                    new_lines.append('                color: {text_color};\n')
                    new_lines.append('            }}"""\n')
                    new_lines.append('            \n')
                    new_lines.append('            self.status_bird_risk.setStyleSheet(style)\n')
                    
                    # format() 호출들을 건너뛰기
                    while i < len(lines) and 'setStyleSheet' not in lines[i]:
                        i += 1
                    i += 1  # setStyleSheet 라인도 건너뛰기
                    
                # 활주로 부분
                elif 'status in [' in if_line:
                    # 활주로 alpha 또는 bravo 판별
                    if 'RWY_A_' in if_line:
                        widget_name = 'status_runway_a'
                    else:
                        widget_name = 'status_runway_b'
                    
                    new_lines.append('            # 색상 설정 (원래 UI 스타일 유지하면서 색상만 변경)\n')
                    new_lines.append('            if status in ["RWY_A_CLEAR", "CLEAR"] if "RWY_A_" in str(status) else status in ["RWY_B_CLEAR", "CLEAR"]:\n')
                    new_lines.append('                border_color = "#006600"\n')
                    new_lines.append('                text_color = "#00ff00"\n')
                    new_lines.append('            else:\n')
                    new_lines.append('                border_color = "#cc0000"\n')
                    new_lines.append('                text_color = "#ff4444"\n')
                    new_lines.append('            \n')
                    new_lines.append('            style = f"""QLabel {{\n')
                    new_lines.append('                font-weight: bold;\n')
                    new_lines.append('                background-color: #000800;\n')
                    new_lines.append('                border: 2px solid {border_color};\n')
                    new_lines.append('                border-radius: 6px;\n')
                    new_lines.append('                padding: 8px;\n')
                    new_lines.append('                font-family: "Courier New", monospace;\n')
                    new_lines.append('                color: {text_color};\n')
                    new_lines.append('            }}"""\n')
                    new_lines.append('            \n')
                    new_lines.append(f'            self.{widget_name}.setStyleSheet(style)\n')
                    
                    # format() 호출들을 건너뛰기
                    while i < len(lines) and 'setStyleSheet' not in lines[i]:
                        i += 1
                    i += 1  # setStyleSheet 라인도 건너뛰기
                else:
                    new_lines.append(line)
                    i += 1
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    # 파일 쓰기
    with open('pilot_gui.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ pilot_gui.py 수정 완료!")

if __name__ == "__main__":
    fix_pilot_gui() 