from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta  # timedelta를 사용하여 어제 날짜 계산
import pytz
import os

# 웹사이트 로그인 및 크롤링
def crawl_website():
    # Selenium 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 화면 없이 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(executable_path='/usr/bin/chromedriver')  # GitHub Actions 환경에 맞게 경로 설정
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 1. 페이지 접속
    driver.get("https://www.dailyvet.co.kr/login?redirect=https://www.dailyvet.co.kr/life?cat=death")

    # 2. 로그인 정보 입력
    user_id_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="user_id"]'))
    )
    user_pw_input = driver.find_element(By.XPATH, '//*[@id="user_pw"]')
    user_id_input.send_keys(os.environ['USER_ID'])
    user_pw_input.send_keys(os.environ['USER_PW'])

    # 로그인 버튼 클릭
    login_button = driver.find_element(By.XPATH, '//*[@id="primary"]/div/div/div[1]/form/input[2]')
    login_button.click()

    # 3. 로그인 후 리다이렉션 대기
    time.sleep(5)

    # 4. //*[@id="mh-board"] 하위의 모든 섹션 반복 크롤링
    all_items = driver.find_elements(By.XPATH, '//*[@id="mh-board"]//div[contains(@class, "single-board-item")]')

    data = []
    # 한국 시간(KST)으로 어제 날짜 설정
    kst = pytz.timezone('Asia/Seoul')
    yesterday = (datetime.now(kst) - timedelta(days=1)).date()  # 어제 날짜를 datetime 객체로 가져오기

    for item in all_items:
        try:
            # 각 아이템 내에서 제목, 링크, 날짜를 찾음
            title = item.find_element(By.XPATH, './div[2]/a/span').text.strip()
            link = item.find_element(By.XPATH, './div[2]/a').get_attribute("href")
            raw_date = item.find_element(By.XPATH, './div[3]/div[1]').text.strip()

            # "등록일 - YYYY.MM.DD" 형식에서 날짜만 추출
            extracted_date = raw_date.split(" - ")[1]  # 'YYYY.MM.DD'만 추출
            # 추출된 문자열을 날짜 객체로 변환
            crawled_date = datetime.strptime(extracted_date, "%Y.%m.%d").date()

            # 디버깅을 위한 로그 출력 (값과 데이터 타입을 함께 출력)
            print(f"raw_date (값): {raw_date}, (타입): {type(raw_date)}")
            print(f"yesterday (값): {yesterday}, (타입): {type(yesterday)}")
            print(f"crawled_date (값): {crawled_date}, (타입): {type(crawled_date)}")

            # 날짜가 어제와 일치할 때만 데이터를 추가
            if crawled_date == yesterday:
                data.append([title, link, crawled_date])

        except Exception as e:
            print(f"데이터를 추출하는 중 오류 발생: {e}")

    driver.quit()  # 브라우저 종료
    return data

# HTML 형식의 테이블로 변환
def format_data_as_table(data):
    table = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    table += "<tr><th>제목</th><th>링크</th><th>날짜</th></tr>"  # 테이블 헤더 추가

    for row in data:
        table += f"<tr><td>{row[0]}</td><td><a href='{row[1]}'>{row[1]}</a></td><td>{row[2]}</td></tr>"

    table += "</table>"
    return table

# 이메일 전송 (첨부 파일 없이, 표를 본문에 포함)
def send_email_with_table(table_html):
    sender = os.environ['SENDER']  # 환경 변수에서 발신자 이메일 가져오기
    receiver = os.environ['RECEIVER']  # 환경 변수에서 수신자 이메일 가져오기
    cc_receiver = os.environ['CC_RECEIVER']  # 환경 변수에서 참조 이메일 가져오기

    subject = "데일리벳 부고게시판에 어제 업데이트된 내역이 있습니다."
    body = f"<p>어제 날짜의 크롤링된 데이터가 아래 표로 정리되었습니다.</p>{table_html}"

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Cc'] = cc_receiver
    msg['Subject'] = subject

    # 이메일 본문에 HTML 테이블 포함
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, os.environ['EMAIL_PASSWORD'])  # 앱 비밀번호 사용
            server.sendmail(sender, [receiver, cc_receiver], msg.as_string())  # CC 포함하여 전송
        print(f"이메일이 {receiver}와 {cc_receiver}로 전송되었습니다.")
    except Exception as e:
        print(f"이메일 전송 실패: {e}")

# 메인 실행 로직
def main():
    data = crawl_website()

    if data:
        # 데이터를 HTML 형식의 테이블로 변환
        table_html = format_data_as_table(data)
        # 이메일로 테이블 전송
        send_email_with_table(table_html)
    else:
        print("어제 날짜에 해당하는 데이터가 없습니다.")

if __name__ == "__main__":
    main()
