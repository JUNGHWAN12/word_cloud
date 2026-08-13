import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from wordcloud import WordCloud


TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=KR"
TRENDS_NAMESPACE = "https://trends.google.com/trending/rss"
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/"
    "NanumGothic-Regular.ttf"
)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


st.set_page_config(
    page_title="대한민국 실시간 검색 트렌드 워드클라우드",
    page_icon="🔥",
    layout="centered",
)

st.title("🔥 대한민국 실시간 검색 트렌드")
st.write(
    "Google Trends의 대한민국 인기 급상승 검색어를 검색량에 따라 "
    "워드클라우드로 표현합니다."
)


def parse_traffic(value: str) -> int:
    """RSS 검색량 문자열(예: 20,000+, 10만+, 5K+)을 정수로 변환한다."""
    normalized = value.strip().replace(",", "").replace("+", "").replace(" ", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)(만|천|[KkMm])?", normalized)
    if not match:
        return 1

    number = float(match.group(1))
    unit = match.group(2)
    multipliers = {
        "만": 10_000,
        "천": 1_000,
        "K": 1_000,
        "k": 1_000,
        "M": 1_000_000,
        "m": 1_000_000,
    }
    return max(1, int(number * multipliers.get(unit, 1)))


def find_approx_traffic(item: ET.Element) -> str:
    traffic = item.findtext(f"{{{TRENDS_NAMESPACE}}}approx_traffic")
    if traffic:
        return traffic

    # Google이 네임스페이스 표기만 변경하는 경우에도 요소의 로컬 이름으로 찾는다.
    for child in item:
        if child.tag.rsplit("}", 1)[-1] == "approx_traffic":
            return child.text or ""
    return ""


@st.cache_data(ttl=600, show_spinner=False)
def get_trends_data() -> dict[str, int]:
    response = requests.get(
        TRENDS_RSS_URL,
        headers=REQUEST_HEADERS,
        timeout=15,
    )
    response.raise_for_status()

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise RuntimeError("Google Trends RSS 응답을 XML로 해석할 수 없습니다.") from exc

    words_freq: dict[str, int] = {}
    for item in root.findall(".//item"):
        keyword = (item.findtext("title") or "").strip()
        if not keyword:
            continue

        traffic = parse_traffic(find_approx_traffic(item))
        words_freq[keyword] = max(traffic, words_freq.get(keyword, 0))

    if not words_freq:
        raise RuntimeError("Google Trends RSS에서 검색어를 찾지 못했습니다.")

    return words_freq


@st.cache_resource(show_spinner=False)
def get_korean_font() -> str:
    """배포 환경에서도 한글을 표시할 수 있도록 나눔고딕을 준비한다."""
    font_path = Path(tempfile.gettempdir()) / "NanumGothic-Regular.ttf"
    if font_path.exists() and font_path.stat().st_size > 100_000:
        return str(font_path)

    response = requests.get(FONT_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    if len(response.content) <= 100_000:
        raise RuntimeError("다운로드한 한글 폰트 파일이 올바르지 않습니다.")

    font_path.write_bytes(response.content)
    return str(font_path)


try:
    with st.spinner("Google Trends 데이터를 불러오는 중입니다..."):
        trends_data = get_trends_data()
except Exception as exc:
    st.error("Google Trends 데이터를 불러오지 못했습니다.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.info("잠시 후 다시 시도하거나 네트워크 연결 상태를 확인해 주세요.")
    st.stop()


try:
    font_path = get_korean_font()
    wordcloud = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        background_color="white",
        colormap="Dark2",
        max_words=50,
        prefer_horizontal=0.9,
    ).generate_from_frequencies(trends_data)
except Exception as exc:
    st.error("워드클라우드를 생성하지 못했습니다.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.stop()


st.subheader("오늘의 인기 검색어")
fig, ax = plt.subplots(figsize=(10, 5))
ax.imshow(wordcloud, interpolation="bilinear")
ax.axis("off")
fig.tight_layout(pad=0)
st.pyplot(fig, clear_figure=True)
plt.close(fig)

st.caption(
    "데이터 출처: [Google Trends 인기 급상승 검색어]"
    "(https://trends.google.com/trending?geo=KR) · 약 10분간 캐시됩니다."
)

with st.expander("상세 검색량 데이터 확인하기"):
    dataframe = pd.DataFrame(
        trends_data.items(),
        columns=["검색어", "검색량(대략)"],
    ).sort_values(by="검색량(대략)", ascending=False, ignore_index=True)
    dataframe["검색량(대략)"] = dataframe["검색량(대략)"].map(
        lambda value: f"{value:,}"
    )
    st.dataframe(dataframe, use_container_width=True, hide_index=True)
