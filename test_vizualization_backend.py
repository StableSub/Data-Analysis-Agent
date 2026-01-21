import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# 백엔드 주소 설정
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Manual Vizualization Tester", layout="wide")
st.title("📊 수동 시각화 기능 테스트 도구")

# 1. 데이터셋 업로드 섹션
st.sidebar.header("1. 데이터셋 준비")
uploaded_file = st.sidebar.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file:
    if st.sidebar.button("서버로 업로드"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
        response = requests.post(f"{BASE_URL}/datasets/", files=files)
        if response.status_code == 200:
            st.sidebar.success(f"업로드 성공! ID: {response.json()['source_id']}")
        else:
            st.sidebar.error("업로드 실패")

# 2. 데이터셋 목록 및 선택
st.sidebar.markdown("---")
if st.sidebar.button("목록 새로고침"):
    st.rerun()

list_res = requests.get(f"{BASE_URL}/datasets/")
if list_res.status_code == 200:
    datasets = list_res.json()["items"]
    ds_options = {f"{d['filename']} ({d['source_id'][:8]})": d['source_id'] for d in datasets}
    selected_ds_name = st.sidebar.selectbox("테스트할 데이터셋 선택", options=list(ds_options.keys()))
    source_id = ds_options[selected_ds_name] if selected_ds_name else None
else:
    st.sidebar.warning("데이터셋 목록을 가져올 수 없습니다.")
    source_id = None

# 3. 시각화 설정 및 테스트
if source_id:
    # 컬럼 정보 가져오기 (샘플 API 활용)
    sample_res = requests.get(f"{BASE_URL}/datasets/{source_id}/sample")
    if sample_res.status_code == 200:
        columns = sample_res.json()["columns"]
        
        st.subheader(f"📍 설정: {selected_ds_name}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_type = st.selectbox("차트 유형", ["bar", "line", "pie", "scatter", "heatmap"])
        with col2:
            x_col = st.selectbox("X축 컬럼", columns)
            y_col = st.selectbox("Y축 컬럼", columns)
        with col3:
            color_col = st.selectbox("Color (Optional)", ["None"] + columns)
            limit = st.number_input("데이터 제한(Limit)", value=500)

        # 4. 시각화 실행
        if st.button("시각화 실행 (API 호출)"):
            payload = {
                "source_id": source_id,
                "chart_type": chart_type,
                "columns": {
                    "x": x_col,
                    "y": y_col,
                    "color": color_col if color_col != "None" else None
                },
                "limit": limit
            }
            
            with st.spinner("API 요청 중..."):
                viz_res = requests.post(f"{BASE_URL}/vizualization/manual", json=payload)
            
            if viz_res.status_code == 200:
                res_data = viz_res.json()
                df = pd.DataFrame(res_data["data"])
                
                st.success(f"성공! 데이터 {len(df)}건 수신.")
                
                # Plotly로 실제 렌더링 확인
                if chart_type == "bar":
                    fig = px.bar(df, x=x_col, y=y_col, color=None if color_col=="None" else color_col)
                elif chart_type == "line":
                    fig = px.line(df, x=x_col, y=y_col, color=None if color_col=="None" else color_col)
                elif chart_type == "pie":
                    fig = px.pie(df, names=x_col, values=y_col)
                elif chart_type == "scatter":
                    fig = px.scatter(df, x=x_col, y=y_col, color=None if color_col=="None" else color_col)
                else:
                    fig = px.density_heatmap(df, x=x_col, y=y_col)
                
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("JSON 응답 데이터 보기"):
                    st.json(res_data)
            else:
                st.error(f"에러 발생: {viz_res.status_code}")
                st.json(viz_res.json())
    else:
        st.error("데이터셋 샘플을 불러올 수 없습니다.")