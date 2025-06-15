from flask import Flask, render_template, request
import pandas as pd
import os
from datetime import datetime
app = Flask(__name__)


# 王昱凱負責；🔍 健康異常判斷函式
# 輸入血壓/心率/體溫，回傳異常提醒清單
def check_health_alert(bp, hr, temp):
    alerts = []

    # 血壓格式解析與判斷
    try:
        systolic, diastolic = map(int, bp.split('/'))
        if systolic > 140 or diastolic > 90:
            alerts.append("⚠️ 血壓過高")
        elif systolic < 90 or diastolic < 60:
            alerts.append("⚠️ 血壓過低")
    except:
        alerts.append("⚠️ 血壓格式錯誤（請用 120/80 格式）")

    # 心率判斷
    try:
        hr = int(hr)
        if hr > 100:
            alerts.append("⚠️ 心率過快")
        elif hr < 60:
            alerts.append("⚠️ 心率過慢")
    except:
        alerts.append("⚠️ 心率格式錯誤")

    # 體溫判斷
    try:
        temp = float(temp)
        if temp > 37.5:
            alerts.append("⚠️ 體溫過高")
        elif temp < 35:
            alerts.append("⚠️ 體溫過低")
    except:
        alerts.append("⚠️ 體溫格式錯誤")

    return alerts

@app.route('/')
def index():
    return render_template('index.html')

# 1.李昊恆負責；病歷查詢功能
@app.route('/search', methods=['GET', 'POST'])
def search():
    patient = None
    searched = False  # 用來追蹤是否已送出查詢

    if request.method == 'POST':
        query = request.form['query'].strip()
        searched = True  # 表示用戶進行了查詢

        # 讀取 CSV 檔案
        df = pd.read_csv('模擬病歷資料_UTF8_BOM.csv', encoding='utf-8-sig')

        # 清理資料中的空格與全形空格
        df['姓名'] = df['姓名'].astype(str).str.replace('\u3000', '').str.strip()
        df['身分證'] = df['身分證'].astype(str).str.strip()
        query = query.replace('\u3000', '').strip()

        # 查詢姓名或身分證欄位
        result = df[(df['姓名'] == query) | (df['身分證'] == query)]

        if not result.empty:
            patient = result.iloc[0].to_dict()

    return render_template('result.html', patient=patient, searched=searched)

# 2.王昱凱負責；健康紀錄功能：紀錄每日健康數據，判斷是否異常
health_csv = 'health_log.csv'

@app.route('/health_log', methods=['GET', 'POST'])
def health_log():
    alerts = []

    if request.method == 'POST':
        name  = request.form['name']
        bp    = request.form['bp']
        hr    = request.form['hr']
        temp  = request.form['temp']
        date  = datetime.now().strftime('%Y-%m-%d')

        # 判斷是否異常
        alerts = check_health_alert(bp, hr, temp)

        # 新增紀錄
        new_record = pd.DataFrame([{
            '姓名': name,
            '日期': date,
            '血壓': bp,
            '心率': hr,
            '體溫': temp
        }])

        # 寫入 CSV（第一次建立或追加）
        if not os.path.exists(health_csv):
            new_record.to_csv(health_csv, index=False, encoding='utf-8-sig')
        else:
            new_record.to_csv(
                health_csv, mode='a', index=False, header=False, encoding='utf-8-sig'
            )

    return render_template('health_log.html', alerts=alerts)

# 3.吳建佑負責；藥物劑量計算功能
@app.route('/drug_calc', methods=['GET', 'POST'])
def drug_calc():
    # 安全讀取 CSV，防止亂碼與空白行
    try:
        df = pd.read_csv('medications.csv', encoding='utf-8-sig')
        df = df.dropna(subset=['藥物名稱'])  # 去除空白藥名行
        df['藥物名稱'] = df['藥物名稱'].str.strip()
    except Exception as e:
        return f"❌ 無法讀取藥物資料表：{str(e)}"

    if request.method == 'POST':
        name = request.form['name']
        try:
            age = float(request.form['age'])
            weight = float(request.form['weight'])
            med_name = request.form['med_name'].strip()
        except ValueError:
            return render_template('drug_calc.html', medications=df['藥物名稱'].tolist(),
                                   error="請輸入正確的數值格式")

        # 查詢藥物資料
        med_row = df[df['藥物名稱'] == med_name]
        if med_row.empty:
            return render_template('drug_calc.html', medications=df['藥物名稱'].tolist(),
                                   error=f"找不到藥物：{med_name}")
        med = med_row.iloc[0]

        # 驗證年齡限制
        age_limit_str = str(med.get('適用年齡', '')).strip()
        try:
            if '歲以上' in age_limit_str:
                min_age = float(age_limit_str.replace('歲以上', '').strip())
                if age < min_age:
                    return render_template('drug_calc.html', medications=df['藥物名稱'].tolist(),
                                           error=f"{med_name} 僅適用於 {min_age} 歲以上，您填寫的年齡為 {age} 歲。")
        except:
            pass  # 若格式異常，不處理限制

        # 安全運算公式
        formula = str(med.get('運算公式', '')).strip()
        try:
            dose = eval(formula, {}, {"體重": weight, "年齡": age})
        except Exception as e:
            return render_template('drug_calc.html', medications=df['藥物名稱'].tolist(),
                                   error=f"計算錯誤：{str(e)}")

        return render_template('drug_calc.html',
                               name=name,
                               age=age,
                               weight=weight,
                               med_name=med_name,
                               dose=round(dose, 2),
                               dose_instruction=med.get('劑量說明', '無資料'),
                               symptoms=med.get('適用症狀', '無資料'),
                               side_effects=med.get('常見副作用', '無資料'),
                               medications=df['藥物名稱'].tolist())

    # GET 請求（顯示初始頁面）
    return render_template('drug_calc.html', medications=df['藥物名稱'].tolist())


# 4.李昱浤負責；線上醫療諮詢（簡單 AI 聊天機器人）
@app.route('/chat', methods=['GET', 'POST'])
def chatbot():
    response_list = []
    
    if request.method == 'POST':
        user_input = request.form['symptom'].strip()
        df = pd.read_csv('chat_data.csv', encoding='utf-8-sig')

        for _, row in df.iterrows():
            # 用模糊比對：只要用戶輸入的關鍵字出現在 row['症狀'] 中就加入結果
            if any(keyword in row['症狀'] for keyword in user_input.split('、')):
                response_list.append(f"🦠 疾病：{row['疾病']}\n💡 建議：{row['治療建議']}")

        if not response_list:
            response = "❗ 很抱歉，目前無法根據輸入判斷疾病，建議您諮詢醫師。"
        else:
            response = "\n\n".join(response_list)

    else:
        response = None

    return render_template('chatbot.html', response=response)

# 5.劉祐恩負責；推薦診所或醫院
@app.route('/clinic_suggest', methods=['GET', 'POST'])
def clinic_suggest():
    clinics = []
    error_msg = None

    if request.method == 'POST':
        area = request.form.get('area', '').strip()
        symptom = request.form.get('symptom', '').strip()

        # 症狀對應科別
        symptom_to_dept = {
            '喉嚨痛': '耳鼻喉科',
            '鼻塞': '耳鼻喉科',
            '發燒': '內科',
            '拉肚子': '內科',
            '牙痛': '牙醫一般科',
            '跌倒': '外科',
            '感冒': '內科',
            '皮膚癢': '皮膚科',
            '月經問題': '婦產科',
            '中醫調理': '中醫一般科'
        }

        matched_dept = None
        for key, dept in symptom_to_dept.items():
            if key in symptom:
                matched_dept = dept
                break

        if not matched_dept:
            error_msg = "❗ 無法判斷症狀對應的科別，請輸入更清楚的症狀"
        else:
            try:
                # 讀取診所資料
                df = pd.read_csv('clean_全台診所分布.csv')
                # 🔹 清理「科別」欄位：去除開頭/結尾空白、雙引號、逗號
                df['科別'] = df['科別'].astype(str).str.replace('"', '').str.strip(',').str.strip()
                # 🔹 清理「縣市區名」欄位（去除空白）
                df['縣市區名'] = df['縣市區名'].astype(str).str.strip()


                # 使用包含文字的模糊比對
                filtered = df[
                    df['縣市區名'].str.contains(area, na=False) &
                    df['科別'].str.contains(matched_dept, na=False)
                ]
                print(f"找到符合條件的診所數量: {len(filtered)}")

                clinics = filtered[['機構名稱', '電話', '地址', '科別']].to_dict(orient='records')

                if len(clinics) == 0:
                    error_msg = f"❗ 找不到 {area} 的 {matched_dept} 診所"

            except Exception as e:
                error_msg = f"❌ 錯誤：{str(e)}"

    return render_template('clinic_suggest.html', clinics=clinics, error_msg=error_msg)


# 啟動 Flask 應用程式
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
