import streamlit as st
import feedparser
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import os
import urllib.request

# 1. 페이지 기본 설정
st.set_page_config(page_title="구글 트렌드 워드클라우드", page_icon="🔥", layout="centered")

st.title("🔥 실시간 대한민국 검색 트렌드")
st.write("구글 트렌드의 일간 검색어 데이터를 기반으로 생성된 워드클라우드입니다.")

# 2. 데이터 수집 함수 (10분 단위로 캐싱하여 서버 부하 방지)
@st.cache_data(ttl=600)
def get_trends_data():
    rss_url = 'https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR'
    feed = feedparser.parse(rss_url)
    
    words_freq = {}
    for entry in feed.entries:
        keyword = entry.title
        # '10,000+' 와 같은 문자열에서 숫자만 추출
        traffic_str = getattr(entry, 'ht_approx_traffic', '10000')
        traffic = int(''.join(filter(str.isdigit, traffic_str)))
        words_freq[keyword] = traffic
        
    return words_freq

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
        colormap='Dark2', # 다양한 색상 테마 적용 가능 (예: 'viridis', 'plasma')
        max_words=50,
        prefer_horizontal=0.9 # 가로 글씨 비율 조정
    ).generate_from_frequencies(trends_data)
    
    # matplotlib를 이용해 스트림릿에 이미지 출력
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off') # 축 숨김
    st.pyplot(fig)
    
    # 5. 원본 데이터 확인 탭 제공
    with st.expander("💡 상세 검색량 데이터 확인하기"):
        df = pd.DataFrame(list(trends_data.items()), columns=['검색어', '검색량(회 이상)'])
        df = df.sort_values(by='검색량(회 이상)', ascending=False).reset_index(drop=True)
        # 검색량에 쉼표 추가 포맷팅
        df['검색량(회 이상)'] = df['검색량(회 이상)'].apply(lambda x: f"{x:,}")
        st.dataframe(df, use_container_width=True)

else:
    st.error("트렌드 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
