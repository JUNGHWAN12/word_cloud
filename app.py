import streamlit as st
import feedparser
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import os
import urllib.request
import requests # <-- 이 줄이 상단에 추가되어야 합니다.

# 1. 페이지 기본 설정
st.set_page_config(page_title="구글 트렌드 워드클라우드", page_icon="🔥", layout="centered")

st.title("🔥 실시간 대한민국 검색 트렌드")
st.write("구글 트렌드의 일간 검색어 데이터를 기반으로 생성된 워드클라우드입니다.")

# 2. 데이터 수집 함수 (봇 차단 우회 및 예외 처리 추가)
@st.cache_data(ttl=600)
def get_trends_data():
    rss_url = 'https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR'
    
    # 일반 크롬 브라우저인 것처럼 위장
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # requests로 데이터를 먼저 가져온 후 feedparser에 전달
        response = requests.get(rss_url, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        
        words_freq = {}
        for entry in feed.entries:
            keyword = entry.title
            traffic_str = getattr(entry, 'ht_approx_traffic', '10000')
            # 숫자만 깔끔하게 추출 (예: '10,000+' -> 10000)
            traffic = int(''.join(filter(str.isdigit, str(traffic_str))))
            words_freq[keyword] = traffic
            
        return words_freq
        
    except Exception as e:
        print(f"Error fetching data: {e}") # 터미널(콘솔)에 에러 로그 출력
        return {}

# 3. 한글 폰트 자동 다운로드 및 적용 함수 (Streamlit Cloud 환경 대응)
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        # 구글 폰트 저장소에서 나눔고딕 레귤러 다운로드
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(font_url, font_path)
    return font_path

# 4. 메인 화면 렌더링
with st.spinner('구글 트렌드 데이터를 실시간으로 가져오는 중입니다...'):
    trends_data = get_trends_data()

if trends_data:
    st.subheader("📊 오늘의 핫 키워드")
    
    # 워드클라우드 객체 생성
    font_path = get_korean_font()
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        background_color='white',
        colormap='Dark2',
        max_words=50,
        prefer_horizontal=0.9
    ).generate_from_frequencies(trends_data)
    
    # matplotlib를 이용해 스트림릿에 이미지 출력
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)
    
    # 5. 원본 데이터 확인 탭 제공
    with st.expander("💡 상세 검색량 데이터 확인하기"):
        df = pd.DataFrame(list(trends_data.items()), columns=['검색어', '검색량(회 이상)'])
        df = df.sort_values(by='검색량(회 이상)', ascending=False).reset_index(drop=True)
        df['검색량(회 이상)'] = df['검색량(회 이상)'].apply(lambda x: f"{x:,}")
        st.dataframe(df, use_container_width=True)

else:
    st.error("트렌드 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
