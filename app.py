import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import os
import urllib.request
import requests
import json # JSON 데이터 파싱을 위해 추가

# 1. 페이지 기본 설정
st.set_page_config(page_title="구글 트렌드 워드클라우드", page_icon="🔥", layout="centered")

st.title("🔥 실시간 대한민국 검색 트렌드")
st.write("구글 트렌드의 일간 검색어 데이터를 기반으로 생성된 워드클라우드입니다.")

# 2. 데이터 수집 함수 (JSON API 우회 접근)
@st.cache_data(ttl=600)
def get_trends_data():
    # 구글 트렌드 내부 JSON API 주소
    api_url = 'https://trends.google.com/trends/api/dailytrends?hl=ko&tz=-540&geo=KR'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        raw_text = response.text
        
        # 구글 API는 보안을 위해 응답 텍스트 맨 앞에 ")]}',\n" 같은 쓰레기 값을 붙여서 보냅니다.
        # 이를 제거해야 정상적인 JSON으로 변환할 수 있습니다.
        if raw_text.startswith(")]}',"):
            raw_text = raw_text.split('\n', 1)[1]
            
        data = json.loads(raw_text)
        words_freq = {}
        
        # JSON 데이터 구조 탐색
        days = data.get('default', {}).get('trendingSearchesDays', [])
        for day in days:
            searches = day.get('trendingSearches', [])
            for search in searches:
                keyword = search.get('title', {}).get('query', '')
                traffic_str = search.get('formattedTraffic', '0')
                
                # "10만+", "5천+", "10K+", "1M+" 등 다양한 텍스트 형태를 숫자로 변환
                traffic_clean = traffic_str.replace('+', '').replace(',', '')
                traffic = 0
                if '만' in traffic_clean:
                    traffic = int(float(traffic_clean.replace('만', '')) * 10000)
                elif '천' in traffic_clean:
                    traffic = int(float(traffic_clean.replace('천', '')) * 1000)
                elif 'K' in traffic_clean.upper():
                    traffic = int(float(traffic_clean.upper().replace('K', '')) * 1000)
                elif 'M' in traffic_clean.upper():
                    traffic = int(float(traffic_clean.upper().replace('M', '')) * 1000000)
                else:
                    try:
                        traffic = int(traffic_clean)
                    except ValueError:
                        traffic = 10000
                
                # 중복되지 않는 키워드만 딕셔너리에 추가
                if keyword and keyword not in words_freq:
                    words_freq[keyword] = traffic
                    
        return words_freq
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {}

# 3. 한글 폰트 자동 다운로드 및 적용 함수
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(font_url, font_path)
    return font_path

# 4. 메인 화면 렌더링
with st.spinner('구글 트렌드 데이터를 실시간으로 가져오는 중입니다...'):
    trends_data = get_trends_data()

if trends_data:
    st.subheader("📊 오늘의 핫 키워드")
    
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
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)
    
    # 5. 원본 데이터 표
    with st.expander("💡 상세 검색량 데이터 확인하기"):
        df = pd.DataFrame(list(trends_data.items()), columns=['검색어', '검색량(회 이상)'])
        df = df.sort_values(by='검색량(회 이상)', ascending=False).reset_index(drop=True)
        df['검색량(회 이상)'] = df['검색량(회 이상)'].apply(lambda x: f"{x:,}")
        st.dataframe(df, use_container_width=True)

else:
    st.error("트렌드 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
