from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox,
                             QStackedWidget, QFrame, QTextEdit, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QDialogButtonBox, QProgressBar, QFileDialog,
                             QApplication)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction, QIcon, QFont

from ..config.settings import Settings
from ..api.criminal_ip import CriminalIPAPI
import csv
import os
import multiprocessing
from functools import partial
import atexit

class IPSearchWorker(QThread):
    """IP 검색을 위한 작업자 스레드"""
    progress = Signal(int, int)  # 현재 진행, 전체 개수
    result = Signal(str, dict)  # IP, 결과 데이터
    error = Signal(str, str)  # IP, 에러 메시지
    finished = Signal()
    
    def __init__(self, api_key, ip_list):
        super().__init__()
        self.api_key = api_key
        self.ip_list = ip_list
        self.process_count = min(multiprocessing.cpu_count(), len(ip_list))
        self._is_running = True
    
    @staticmethod
    def process_ip(args):
        """단일 IP 처리 함수 (정적 메서드)"""
        ip, api_key = args
        try:
            # API 객체 생성
            api = CriminalIPAPI(api_key)
            # IP 상세 정보 조회
            summary_result = api.ip_summary(ip)
            return ip, summary_result, None
        except Exception as e:
            return ip, None, str(e)
    
    def run(self):
        total = len(self.ip_list)
        processed = 0
        
        # API 키와 IP 쌍으로 인자 생성
        args = [(ip, self.api_key) for ip in self.ip_list]
        
        # 멀티프로세싱 풀 생성
        with multiprocessing.Pool(processes=self.process_count) as pool:
            # 비동기 작업 시작
            for ip, data, error in pool.imap_unordered(self.process_ip, args):
                if not self._is_running:
                    break
                    
                processed += 1
                
                if error:
                    self.error.emit(ip, error)
                else:
                    self.result.emit(ip, data)
                
                # 진행 상황 업데이트
                self.progress.emit(processed, total)
        
        self.finished.emit()
    
    def stop(self):
        """스레드 중지"""
        self._is_running = False

# 전역 스레드 관리자
class ThreadManager(QObject):
    def __init__(self):
        super().__init__()
        self.threads = []
    
    def add_thread(self, thread):
        self.threads.append(thread)
    
    def cleanup(self):
        for thread in self.threads:
            if thread and thread.isRunning():
                thread.stop()
                thread.wait()
        self.threads.clear()

# 전역 스레드 관리자 인스턴스
thread_manager = ThreadManager()

# 애플리케이션 종료 시 스레드 정리
def cleanup_threads():
    thread_manager.cleanup()

# 애플리케이션 종료 시 정리 함수 등록
atexit.register(cleanup_threads)

class IPDetailDialog(QDialog):
    def __init__(self, ip_data, parent=None):
        super().__init__(parent)
        ip = ip_data.get('summary', {}).get('ip', 'N/A')
        self.setWindowTitle(f"IP 상세 정보 - {ip}")
        self.setMinimumSize(800, 600)
        self.init_ui(ip_data)
    
    def init_ui(self, ip_data):
        layout = QVBoxLayout(self)
        
        # 상세 정보 표시
        text = QTextEdit()
        text.setReadOnly(True)
        text.setObjectName("detail-text")
        
        # JSON 데이터 포맷팅
        import json
        formatted_json = json.dumps(ip_data, indent=2, ensure_ascii=False)
        text.setText(formatted_json)
        
        layout.addWidget(text)
        
        # 닫기 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.api = None
        self.search_worker = None
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Criminal IP API Tool")
        self.setMinimumSize(1200, 800)
        
        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 사이드바 생성
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 메인 콘텐츠 영역
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)
        
        # IP 조회 페이지
        ip_search_page = self.create_ip_search_page()
        self.content_stack.addWidget(ip_search_page)
        
        # API 키 설정 페이지
        api_settings_page = self.create_api_settings_page()
        self.content_stack.addWidget(api_settings_page)
        
        # 기본 페이지
        default_page = self.create_default_page()
        self.content_stack.addWidget(default_page)
        
        # 레이아웃 비율 설정
        main_layout.setStretch(0, 1)  # 사이드바
        main_layout.setStretch(1, 4)  # 메인 콘텐츠
    
    def create_ip_search_page(self):
        """IP 조회 페이지 생성"""
        page = QWidget()
        page.setObjectName("content-page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 타이틀
        title = QLabel("IP 주소 조회")
        title.setObjectName("page-title")
        layout.addWidget(title)
        
        # 설명 텍스트
        description = QLabel("조회하려는 IP 주소를 입력하세요. (여러 IP는 줄바꿈으로 구분)")
        description.setObjectName("description-text")
        layout.addWidget(description)
        
        layout.addSpacing(20)
        
        # IP 입력 섹션
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setSpacing(10)
        
        self.ip_input = QTextEdit()
        self.ip_input.setObjectName("ip-input")
        self.ip_input.setPlaceholderText("IP 주소를 입력하세요 (예: 8.8.8.8)\n여러 IP는 줄바꿈으로 구분")
        self.ip_input.setMaximumHeight(100)
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(10)
        
        self.search_button = QPushButton("조회")
        self.search_button.setObjectName("primary-button")
        self.search_button.clicked.connect(self.search_ip)
        
        self.export_button = QPushButton("CSV 내보내기")
        self.export_button.setObjectName("secondary-button")
        self.export_button.clicked.connect(self.export_to_csv)
        self.export_button.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress-bar")
        self.progress_bar.setVisible(False)
        
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.progress_bar)
        
        input_layout.addWidget(self.ip_input)
        input_layout.addWidget(button_container)
        
        layout.addWidget(input_container)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setObjectName("result-table")
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels(["IP 주소", "국가", "도시", "ISP", "열린 포트", "VPN", "모바일", "상세보기"])
        
        # 열 너비 설정
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # IP 주소
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)   # 국가
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # 도시
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # ISP
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)   # 열린 포트
        self.result_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)   # VPN
        self.result_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)   # 모바일
        self.result_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)   # 상세보기
        
        # 고정 열 너비 설정
        self.result_table.setColumnWidth(1, 60)  # 국가
        self.result_table.setColumnWidth(4, 80)  # 열린 포트
        self.result_table.setColumnWidth(5, 60)  # VPN
        self.result_table.setColumnWidth(6, 60)  # 모바일
        self.result_table.setColumnWidth(7, 100) # 상세보기
        
        # 테이블 셀 클릭 이벤트 연결
        self.result_table.cellClicked.connect(self.handle_cell_click)
        
        layout.addWidget(self.result_table)
        
        return page
    
    def search_ip(self):
        """IP 주소 조회"""
        if not self.api:
            QMessageBox.warning(self, "경고", "먼저 API 키를 설정해주세요.")
            return
        
        ip_text = self.ip_input.toPlainText().strip()
        if not ip_text:
            QMessageBox.warning(self, "경고", "IP 주소를 입력해주세요.")
            return
        
        # IP 주소 목록 생성
        ip_list = [ip.strip() for ip in ip_text.split('\n') if ip.strip()]
        
        # 테이블 초기화
        self.result_table.setRowCount(0)
        
        # 프로그레스바 설정
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(ip_list))
        self.progress_bar.setValue(0)
        
        # 검색 버튼 비활성화
        self.search_button.setEnabled(False)
        
        # 이전 작업자 스레드가 있으면 중지
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            # 스레드가 완전히 종료될 때까지 기다림
            self.search_worker.wait()
        
        # 작업자 스레드 생성 및 시작
        self.search_worker = IPSearchWorker(self.api.api_key, ip_list)
        self.search_worker.progress.connect(self.update_progress)
        self.search_worker.result.connect(self.add_result)
        self.search_worker.error.connect(self.show_error)
        self.search_worker.finished.connect(self.search_finished)
        
        # 스레드 관리자에 추가
        thread_manager.add_thread(self.search_worker)
        
        self.search_worker.start()
    
    def update_progress(self, current, total):
        """진행 상황 업데이트"""
        self.progress_bar.setValue(current)
    
    def add_result(self, ip, data):
        """검색 결과 추가"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        # 기본 정보 추가
        ip_item = QTableWidgetItem(ip)
        ip_item.setTextAlignment(Qt.AlignCenter)
        ip_item.setFlags(ip_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 0, ip_item)
        
        # whois 데이터 가져오기
        whois_data = data.get('whois', {}).get('data', [{}])[0] if data.get('whois', {}).get('data') else {}
        
        # 국가 정보
        country = whois_data.get('org_country_code', 'N/A')
        country_item = QTableWidgetItem(country.upper())
        country_item.setTextAlignment(Qt.AlignCenter)
        country_item.setFlags(country_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 1, country_item)
        
        # 도시 정보
        city = whois_data.get('city', 'N/A')
        city_item = QTableWidgetItem(city)
        city_item.setTextAlignment(Qt.AlignCenter)
        city_item.setFlags(city_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 2, city_item)
        
        # ISP 정보
        isp = whois_data.get('org_name', 'N/A')
        isp_item = QTableWidgetItem(isp)
        isp_item.setTextAlignment(Qt.AlignCenter)
        isp_item.setFlags(isp_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 3, isp_item)
        
        # 열린 포트 수
        open_ports = data.get('port', {}).get('count', 0)
        ports_item = QTableWidgetItem(str(open_ports))
        ports_item.setTextAlignment(Qt.AlignCenter)
        ports_item.setFlags(ports_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 4, ports_item)
        
        # VPN 여부
        is_vpn = data.get('issues', {}).get('is_vpn', False)
        vpn_item = QTableWidgetItem("예" if is_vpn else "아니오")
        vpn_item.setForeground(Qt.red if is_vpn else Qt.green)
        vpn_item.setTextAlignment(Qt.AlignCenter)
        vpn_item.setFlags(vpn_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 5, vpn_item)
        
        # 모바일 여부
        is_mobile = data.get('issues', {}).get('is_mobile', False)
        mobile_item = QTableWidgetItem("예" if is_mobile else "아니오")
        mobile_item.setForeground(Qt.red if is_mobile else Qt.green)
        mobile_item.setTextAlignment(Qt.AlignCenter)
        mobile_item.setFlags(mobile_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        self.result_table.setItem(row, 6, mobile_item)
        
        # 상세보기 텍스트 추가 (링크 대신 일반 텍스트로 변경)
        detail_item = QTableWidgetItem("상세보기")
        detail_item.setTextAlignment(Qt.AlignCenter)
        detail_item.setFlags(detail_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용으로 설정
        detail_item.setForeground(Qt.blue)  # 파란색으로 표시
        self.result_table.setItem(row, 7, detail_item)
        
        # 결과가 있으면 내보내기 버튼 활성화
        self.export_button.setEnabled(True)
    
    def show_error(self, ip, error_msg):
        """에러 메시지 표시"""
        QMessageBox.critical(self, "오류", f"IP {ip} 조회 중 오류가 발생했습니다: {error_msg}")
    
    def search_finished(self):
        """검색 완료 처리"""
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.search_worker = None
    
    def show_ip_detail(self, ip_data):
        """IP 상세 정보 다이얼로그 표시"""
        try:
            dialog = IPDetailDialog(ip_data, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"상세 정보 조회 중 오류가 발생했습니다: {str(e)}")
    
    def create_sidebar(self):
        """사이드바 생성"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 40)
        sidebar_layout.setSpacing(15)
        
        # 로고 또는 타이틀
        title = QLabel("Criminal IP")
        title.setObjectName("sidebar-title")
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)
        
        sidebar_layout.addSpacing(30)
        
        # IP 조회 버튼
        ip_search_btn = QPushButton("IP 조회")
        ip_search_btn.setObjectName("sidebar-button")
        ip_search_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        sidebar_layout.addWidget(ip_search_btn)
        
        # API 키 설정 버튼
        api_key_btn = QPushButton("API 키 설정")
        api_key_btn.setObjectName("sidebar-button")
        api_key_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        sidebar_layout.addWidget(api_key_btn)
        
        # 나중에 추가될 메뉴들을 위한 공간
        sidebar_layout.addStretch()
        
        return sidebar
    
    def create_api_settings_page(self):
        """API 키 설정 페이지 생성"""
        page = QWidget()
        page.setObjectName("content-page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 타이틀
        title = QLabel("API 키 설정")
        title.setObjectName("page-title")
        layout.addWidget(title)
        
        # 설명 텍스트
        description = QLabel("Criminal IP API를 사용하기 위해 API 키를 입력해주세요.")
        description.setObjectName("description-text")
        layout.addWidget(description)
        
        layout.addSpacing(20)
        
        # API 키 입력 섹션
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setSpacing(10)
        
        api_key_label = QLabel("API 키")
        api_key_label.setObjectName("input-label")
        self.api_key_input = QLineEdit()
        self.api_key_input.setObjectName("api-key-input")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("API 키를 입력하세요")
        
        # 저장된 API 키가 있다면 로드
        saved_api_key = self.settings.get_api_key()
        if saved_api_key:
            self.api_key_input.setText(saved_api_key)
            self.api = CriminalIPAPI(saved_api_key)
        
        input_layout.addWidget(api_key_label)
        input_layout.addWidget(self.api_key_input)
        
        layout.addWidget(input_container)
        layout.addSpacing(20)
        
        # 저장 버튼
        save_button = QPushButton("저장")
        save_button.setObjectName("primary-button")
        save_button.clicked.connect(self.save_api_key)
        layout.addWidget(save_button)
        
        layout.addStretch()
        
        return page
    
    def create_default_page(self):
        """기본 페이지 생성"""
        page = QWidget()
        page.setObjectName("content-page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        welcome_text = QLabel("Criminal IP API Tool에 오신 것을 환영합니다")
        welcome_text.setObjectName("welcome-text")
        welcome_text.setAlignment(Qt.AlignCenter)
        
        instruction_text = QLabel("사이드바에서 API 키를 설정해주세요")
        instruction_text.setObjectName("instruction-text")
        instruction_text.setAlignment(Qt.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(welcome_text)
        layout.addSpacing(10)
        layout.addWidget(instruction_text)
        layout.addStretch()
        
        return page
    
    def apply_styles(self):
        """스타일시트 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            
            #sidebar {
                background-color: #2d2d2d;
                border: none;
            }
            
            #sidebar-title {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
            
            #sidebar-button {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }
            
            #sidebar-button:hover {
                background-color: #404040;
            }
            
            #content-page {
                background-color: #2d2d2d;
                border-radius: 8px;
                margin: 20px;
                border: 1px solid #404040;
            }
            
            #page-title {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
            }
            
            #description-text {
                color: #b3b3b3;
                font-size: 14px;
            }
            
            #input-label {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
            
            #api-key-input, #ip-input {
                padding: 12px;
                border: 1px solid #404040;
                border-radius: 4px;
                font-size: 14px;
                background-color: #333333;
                color: #ffffff;
            }
            
            #api-key-input:focus, #ip-input:focus {
                border: 1px solid #505050;
                background-color: #383838;
            }
            
            #primary-button {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            
            #primary-button:hover {
                background-color: #505050;
            }
            
            #primary-button:disabled {
                background-color: #303030;
                color: #808080;
            }
            
            #secondary-button {
                background-color: #303030;
                color: white;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            
            #secondary-button:hover {
                background-color: #383838;
            }
            
            #secondary-button:disabled {
                background-color: #282828;
                color: #606060;
                border-color: #303030;
            }
            
            #welcome-text {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
            }
            
            #instruction-text {
                font-size: 16px;
                color: #b3b3b3;
            }
            
            #result-table {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                gridline-color: #404040;
            }
            
            #result-table::item {
                padding: 8px;
                text-align: center;
            }
            
            #result-table QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
                text-align: center;
            }
            
            #detail-link {
                color: #4a9eff;
                font-size: 12px;
                padding: 0px;
                margin: 0px;
                line-height: 30px;
            }
            
            #detail-link:hover {
                color: #6ab0ff;
                text-decoration: underline;
            }
            
            #detail-text {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 12px;
                font-family: monospace;
                font-size: 14px;
            }
            
            #progress-bar {
                background-color: #333333;
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            
            #progress-bar::chunk {
                background-color: #404040;
                border-radius: 3px;
            }
        """)
    
    def save_api_key(self):
        """API 키 저장"""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "경고", "API 키를 입력해주세요.")
            return
        
        try:
            self.settings.save_api_key(api_key)
            self.api = CriminalIPAPI(api_key)
            QMessageBox.information(self, "성공", "API 키가 저장되었습니다.")
            # API 키 저장 후 기본 페이지로 이동
            self.content_stack.setCurrentIndex(2)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"API 키 저장 중 오류가 발생했습니다: {str(e)}")
    
    def export_to_csv(self):
        """테이블 데이터를 CSV 파일로 내보내기"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV 파일 저장",
            os.path.expanduser("~/Desktop"),
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 헤더 작성
                headers = []
                for col in range(self.result_table.columnCount() - 1):  # 상세보기 버튼 제외
                    headers.append(self.result_table.horizontalHeaderItem(col).text())
                writer.writerow(headers)
                
                # 데이터 작성
                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(self.result_table.columnCount() - 1):  # 상세보기 버튼 제외
                        item = self.result_table.item(row, col)
                        if item:
                            row_data.append(item.text())
                        else:
                            row_data.append('')
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "성공", "CSV 파일이 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 파일 저장 중 오류가 발생했습니다: {str(e)}")
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        # 실행 중인 스레드가 있으면 중지
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            # 스레드가 완전히 종료될 때까지 기다림
            self.search_worker.wait()
            # 스레드 객체 참조 제거
            self.search_worker = None
        
        # 이벤트 처리
        event.accept()

    def handle_cell_click(self, row, column):
        """테이블 셀 클릭 이벤트 처리"""
        # 상세보기 열(7번 열)을 클릭했을 때만 처리
        if column == 7:
            # 해당 행의 IP 주소 가져오기
            ip = self.result_table.item(row, 0).text()
            
            # IP 상세 정보 조회
            try:
                data = self.api.ip_summary(ip)
                self.show_ip_detail(data)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"IP {ip} 상세 정보 조회 중 오류가 발생했습니다: {str(e)}")