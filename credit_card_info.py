## 新規申込顧客がクレジットカードを登録した際に、デビットカードとプリペイドカードを除外し、審査落ちさせるためのスクリプト。
## デビットカードによる未収が問題となりBIN判定によるAPI運用を検討したが、費用の問題で稟議が通らずこちらのスクリプトで対応。
## 日次で自動実行させ、BIN判定を行っている。


import win32com.client as win32
import os
import webbrowser
import time
import datetime
import requests
import pandas as pd
import shutil
import pyautogui
from datetime import datetime, timedelta
from pandas import DataFrame
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
pd.options.display.max_columns = None


today = datetime.now().date()
# today =  today - timedelta(days=1)  ### 過去分抽出用としても利用
yesterday = today - timedelta(days=1) 
today_str = today.strftime("%Y%m%d")
yesterday_str = yesterday.strftime("%Y%m%d")
folder_name = today.strftime("%Y%m")

first_time = "100000"  ### 検索したい時間 10:00:00
last_time = "095959"   ### 検索したい時間 09:59:59
print(yesterday_str)



df_card = pd.read_csv("C:\\Users\\ユーザー名\\Downloads\\credit_card_info\\プリぺ_デビットリスト.csv",encoding="cp932")

# ### クレカリストを準備
# MAX_RETRIES = 3  # 最大リトライ回数
# url = "https://wikiwiki.jp/emvcl/column/bin"
# driver = webdriver.Firefox()

# for attempt in range(MAX_RETRIES):
# 	try:
# 		driver.get(url)
# 		print("Page loaded successfully!")
# 		break  # 正常にロードされたら終了
# 	except TimeoutException:
# 		print(f"Attempt {attempt + 1}: Page load timeout. Retrying...")
# 		time.sleep(2)  # リトライの前に少し待機
# else:
# 	print("Failed to load the page after multiple retries.")

# # <tr>タグをすべて取得
# rows = driver.find_elements(By.TAG_NAME, 'tr')

# # 各<tr>タグのテキストをCSV用のリストとして用意
# table_data = []

# for index, row in enumerate(rows):
# 	# <tr>ごとのテキストを取得し、リストに追加
# 	row_text = row.text
# 	print(f"Row {index}: {row_text}")
# 	table_data.append([row_text])
# driver.quit()


# ### Pandasのデータフレームに変換
# df_card = pd.DataFrame(table_data, columns=["Row_text"])
# df_card = df_card[df_card["Row_text"].str.contains(r' D | P ', na=False)]

# df_card["Row_text"] = df_card["Row_text"].str.replace("-", "").str.replace(" ", "").str.replace("?", "")
# df_card["カード番号"] = df_card["Row_text"].str[:7]
# df_card["種別"] = df_card["カード番号"].str[-1]
# df_card["カード番号"] = df_card["カード番号"].str[:-1]

# df_card = df_card[df_card["種別"].isin(["P", "D"])] 
# df_card["カード番号"] = df_card["カード番号"].astype(int)
# df_card = df_card.drop("Row_text",axis=1)



### クレカの情報を取りに行く
flp = r"\\sample\credit_card_info"
folder_path = os.path.join(flp, folder_name)

### 当月のフォルダが存在しない場合、新しく作成
if not os.path.exists(folder_path):
	os.makedirs(folder_path)
	print(f"Folder {folder_path} has been created.")
else:
	print(f"Folder {folder_path} already exists.")



driver=webdriver.Firefox()
driver.set_window_size(1024,1000)
driver.get('https://card_info/login')
driver.maximize_window()


USERNAME  = 'user'
PASSWORD  = 'pass'

### ログイン用
username_input = driver.find_element(By.XPATH,'//*[@id="username"]')
username_input.send_keys(USERNAME)

password_input = driver.find_element(By.XPATH,'//*[@id="password"]')
password_input.send_keys(PASSWORD)

login_button = driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div/div[3]/div/div[2]/form/fieldset/div[3]/div/button')
login_button.click()
time.sleep(2)

menu_button = driver.find_element(By.XPATH, '/html/body/div[1]/nav/div[2]/ul[1]/li[7]/a')
menu_button.click()
time.sleep(1)
menu_button = driver.find_element(By.XPATH, '/html/body/div[1]/nav/div[2]/ul[1]/li[7]/ul/li/a')
menu_button.click()
time.sleep(1)

menu_button = driver.find_element(By.XPATH, '//*[@id="gmopg_gp_member_searchlog"]')
menu_button.click()

menu_button = driver.find_element(By.XPATH, '//*[@id="memberlog_search_code"]/label[2]')
menu_button.click()

date_time_input = driver.find_element(By.XPATH,'//*[@id="memberlog_search_updatedateStart"]')
date_time_input.send_keys(yesterday_str + first_time)
date_time_input = driver.find_element(By.XPATH,'//*[@id="memberlog_search_updatedateEnd"]')
date_time_input.send_keys(today_str + last_time)
date_time_input.send_keys(Keys.ENTER)
time.sleep(1)


body_element = driver.find_element(By.TAG_NAME, 'body')
body_text = body_element.text


### 検索結果がなければ終了する
if "該当情報はありません" in body_text:

	df_nothing = pd.DataFrame(columns=["処理日時", "決済ID", "カード番号"])
	df_nothing.to_csv(folder_path +"\\credit_card_info_"+ today_str +"_該当なし.csv",encoding="cp932",index=False)

	print("該当情報はありませんでした。ウィンドウを閉じて処理を終了します。")
	driver.quit()

else:
	print("該当情報が見つかりました。処理を続行します。")

	df_sbs_card = pd.DataFrame(columns=["処理日時", "決済ID", "カード番号"])  ### DataFrameを用意し登録情報を蓄積していく
	page_count = 1  ### 初期ページ設定

	while True: ### 検索結果が複数あった場合に備えてページごとにループ処理

		total_icons = len(driver.find_elements(By.CSS_SELECTOR, 'i.icon-zoom-in'))

		for index in range(total_icons): ### 1ページに複数ユーザーが表示されるため一人ずつループ処理
			icons = driver.find_elements(By.CSS_SELECTOR, 'i.icon-zoom-in')
			print(f"Processing icon {index + 1}")
			icons[index].click()

			day_td = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//td[text()="処理日時"]')))
			day_text = day_td.find_element(By.XPATH, 'following-sibling::td').text

			number_td = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//td[text()="会員ID"]')))
			number_text = number_td.find_element(By.XPATH, 'following-sibling::td').text

			card_number_td = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//td[text()="カード番号"]')))
			card_number_text = card_number_td.find_element(By.XPATH, 'following-sibling::td').text

			df_sbs_card = df_sbs_card.append({"処理日時": day_text, "決済ID": number_text, "カード番号": card_number_text},	ignore_index=True)

			back_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-back"]')))
			back_button.click()

			WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'i.icon-zoom-in')))


		### "次へ"ボタンの存在を確認
		try:
			### <li class="next">の中にある<a>を見つけてクリックする
			next_li_tag = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '//li[@class="next"]/a')))
			next_li_tag.click()
			page_count += 1  ### 次のページに進む
			print(f"次のページに進みました: {page_count} ページ")

		except Exception as e:
			print("次のページが存在しないか、クリックできません。ループを終了します。Error:", str(e))
			break


	### 終了メッセージ
	print("抽出完了")
	print(df_sbs_card)
	driver.quit()
	
	df_sbs_card['カード番号'] = df_sbs_card['カード番号'].str[:6]
	df_sbs_card["カード番号"] = df_sbs_card["カード番号"].str.replace('*', '')
	df_sbs_card["カード番号"] = df_sbs_card["カード番号"].astype(int)
	df_sbs_card = df_sbs_card.sort_values('処理日時')

	
	df_sbs_card = pd.merge(df_sbs_card,df_card,on="カード番号",how="left").fillna("-")
	df_sbs_card = df_sbs_card[df_sbs_card['種別'] != '-']
	

	if df_sbs_card.empty: ### merge結果が0なら対象なしのため処理を終了
		df_sbs_card = df_sbs_card.drop(columns=['カード番号'])
		df_sbs_card.to_csv(folder_path +"\\credit_card_info_"+ today_str +"_該当なし.csv",encoding="cp932",index=False)
		print("データフレームは空です。処理を終了します。")
	else:
		### 空でない場合の処理
		
		df_sbs_card = df_sbs_card.drop(columns=['カード番号'])
		df_sbs_card.to_csv(folder_path +"\\credit_card_info_"+ today_str +".csv",encoding="cp932",index=False)


		print("処理完了")
