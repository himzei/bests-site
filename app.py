from flask import Flask, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Flask 애플리케이션 인스턴스 생성
app = Flask(__name__)

# 루트 경로 라우트
@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

# 베스트글 조회 API 엔드포인트
@app.route('/health')
def health():
    """보배드림 베스트글 가져오기"""
    try:
        # 보배드림 베스트글 페이지 URL
        url = 'https://m.bobaedream.co.kr/board/new_writing/best'
        
        # User-Agent 설정 (봇 차단 방지)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 페이지 요청
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # HTTP 에러 체크
        
        # 인코딩 처리: 한글 깨짐 방지
        # 보배드림 모바일 페이지는 보통 UTF-8을 사용하지만, 
        # 인코딩이 제대로 감지되지 않을 수 있으므로 명시적으로 처리
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            # 인코딩이 감지되지 않았거나 잘못 감지된 경우 UTF-8로 설정
            response.encoding = 'utf-8'
        
        # HTML 파싱 (명시적 인코딩 지정)
        # response.content를 사용하여 바이너리 데이터를 직접 디코딩하는 것이 더 안전함
        try:
            html_content = response.content.decode('utf-8')
        except UnicodeDecodeError:
            # UTF-8 디코딩 실패 시 EUC-KR로 시도
            html_content = response.content.decode('euc-kr', errors='replace')
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 베스트글 목록 추출
        best_posts = []
        
        # 게시글 링크 찾기 (보배드림 모바일 페이지 구조)
        # 게시글 링크는 /board/bbs_view/best/ 형태를 가짐
        import re
        post_links = soup.find_all('a', href=re.compile(r'/board/bbs_view/best/'))
        
        # 각 게시글 정보 추출
        for idx, link_elem in enumerate(post_links[:20], 1):  # 최대 20개만 가져오기
            try:
                # 링크 추출
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = f'https://m.bobaedream.co.kr{link}'
                
                # 링크 텍스트에서 정보 추출
                link_text = link_elem.get_text(strip=True)
                
                # 제목 추출 (링크 텍스트의 앞부분, "이미지" 또는 "모바일" 키워드 전까지)
                title = link_text
                # "이미지", "모바일" 등의 키워드 제거
                title = re.sub(r'\s*(이미지|모바일)\s*', ' ', title)
                
                # 작성자, 시간, 조회수, 추천수, 댓글수 추출
                # 패턴: "작성자 시간 조회 숫자 추천 숫자" 또는 "작성자 시간 조회 숫자 추천 숫자 댓글 숫자"
                # 예: "신유머 진짜싼아이 12:50 조회 2760 추천 34"
                
                author = '작성자 없음'
                post_time = '시간 없음'
                views = '조회수 없음'
                likes = '추천수 없음'
                comments = '댓글수 없음'
                
                # 정규표현식으로 정보 추출
                # 작성자 패턴: 보통 카테고리명 + 닉네임 형태 (예: "신유머 진짜싼아이")
                # 시간 패턴: HH:MM 형태
                # 조회수 패턴: "조회 숫자"
                # 추천수 패턴: "추천 숫자"
                
                # 시간 추출 (HH:MM 형식)
                time_match = re.search(r'(\d{1,2}:\d{2})', link_text)
                if time_match:
                    post_time = time_match.group(1)
                
                # 조회수 추출
                view_match = re.search(r'조회\s*(\d+)', link_text)
                if view_match:
                    views = f"{view_match.group(1)}회"
                
                # 추천수 추출
                like_match = re.search(r'추천\s*(\d+)', link_text)
                if like_match:
                    likes = f"{like_match.group(1)}개"
                
                # 댓글수 추출 (있는 경우)
                comment_match = re.search(r'댓글\s*(\d+)', link_text)
                if comment_match:
                    comments = f"{comment_match.group(1)}개"
                
                # 작성자 추출 (시간 앞부분의 텍스트)
                # 구조: "제목 이미지 모바일 카테고리 작성자 시간 조회 추천"
                if time_match:
                    # 시간 앞부분에서 작성자 추출
                    before_time = link_text[:time_match.start()].strip()
                    # 시간 바로 앞의 단어가 작성자 (일반적으로)
                    words = before_time.split()
                    if words:
                        # 마지막 단어가 작성자일 가능성이 높음
                        # 단, "이미지", "모바일", "신유머", "유머" 등의 키워드는 제외
                        keywords_to_skip = ['이미지', '모바일', '신유머', '유머', '자유', '정치', '블박', '뉴스']
                        for word in reversed(words):
                            if word not in keywords_to_skip:
                                author = word
                                break
                
                # 제목 정리 (작성자, 시간, 조회수, 추천수 정보 제거)
                # 제목은 링크 텍스트의 앞부분에 있음
                if time_match:
                    # 시간 이전 부분에서 제목 추출
                    title_part = link_text[:time_match.start()].strip()
                    # 카테고리 키워드 제거
                    title_part = re.sub(r'\s*(이미지|모바일|신유머|유머|자유|정치|블박|뉴스)\s*', ' ', title_part)
                    # 작성자 제거
                    if author != '작성자 없음':
                        title_part = title_part.replace(author, '').strip()
                    title = title_part.strip()
                
                # 제목에서 남은 메타데이터 제거
                title = re.sub(r'\s*조회\s*\d+\s*추천\s*\d+.*$', '', title).strip()
                title = re.sub(r'^\s*\[.*?\]\s*', '', title)  # 앞부분의 [태그] 제거
                
                best_posts.append({
                    '순위': idx,
                    '제목': title,
                    '작성자': author,
                    '작성시간': post_time,
                    '조회수': views,
                    '추천수': likes,
                    '댓글수': comments,
                    '링크': link
                })
            except Exception as e:
                # 개별 게시글 처리 중 에러 발생 시 스킵
                continue
        
        return jsonify({
            'status': 'ok',
            'message': '베스트글을 성공적으로 가져왔습니다',
            '데이터_수집_시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '게시글_수': len(best_posts),
            '게시글_목록': best_posts
        })
        
    except requests.exceptions.RequestException as e:
        # 네트워크 에러 처리
        return jsonify({
            'status': 'error',
            'message': f'페이지를 가져오는 중 오류가 발생했습니다: {str(e)}'
        }), 500
    except Exception as e:
        # 기타 에러 처리
        return jsonify({
            'status': 'error',
            'message': f'처리 중 오류가 발생했습니다: {str(e)}'
        }), 500

# Flask 서버 실행
if __name__ == '__main__':
    # 개발 모드로 실행 (디버그 모드 활성화)
    # 포트 5000은 macOS AirPlay Receiver가 사용할 수 있으므로 5001로 변경
    app.run(debug=True, host='0.0.0.0', port=5001)
