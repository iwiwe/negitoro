
## WiFi契約者の過去の解約傾向をもとに、各社ごとの月次解約件数を予測する機械学習モデル。
## 解約件数を把握することで、解約予算の設定、営業・サポートリソースの最適配分や解約抑止施策の立案を目的としている。
## モデル：LinearRegression（線形回帰） モデル単位：会社別に個別モデル構築  予測対象：当月の解約件数
## 線形回帰により、モデルの出力をそのまま解釈可能（予測に効いている変数が分かる）特に 登録種別, 商材区分, 経過月 によって解約傾向は大きく異なるため、これらは必須の特徴量と考える。
## 経過月² や 月 を導入することで、非線形な解約ピークや季節性にも対応し、解約件数の変動が激しい会社については、予測のブレが大きくなる傾向があるため、MAPEだけでなくMAEにも注目したい。

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from joblib import dump
import numpy as np
pd.options.display.max_columns = None


flp = "\\\\sample\\"


df = pd.read_csv(flp + "moto.csv", encoding="cp932")


df = df[df["解約年月"] != "継続中"].copy()
df["解約年月"] = df["解約年月"].astype(int)

## 経過月と2乗項を算出
df["課金開始年月"] = df["課金開始年月"].astype(int)
df["経過月"] = (df["解約年月"] // 100 - df["課金開始年月"] // 100) * 12 + (df["解約年月"] % 100 - df["課金開始年月"] % 100)
df["経過月2乗"] = df["経過月"] ** 2


df["年"] = df["解約年月"] // 100
df["月"] = df["解約年月"] % 100

## 月別・会社別に解約件数と特徴量を集計
group_cols = ["簡易会社名", "解約年月"]
agg_cols = {
	"経過月": "mean",
	"経過月2乗": "mean",
	"月": "mean",
	"商材区分": lambda x: x.mode().iloc[0] if not x.mode().empty else "",
	"登録種別": lambda x: x.mode().iloc[0] if not x.mode().empty else "",
	"契約者ID": "count"
}
df_summary = df.groupby(group_cols).agg(agg_cols).reset_index()
df_summary = df_summary.rename(columns={"契約者ID": "解約件数"})
df_summary["年"] = df_summary["解約年月"] // 100

df_summary["月"] = df_summary["解約年月"] % 100

## 特徴量エンコーディング
cat_cols = ["登録種別", "日報用初回商材区分"]
df_encoded = pd.get_dummies(df_summary, columns=cat_cols, drop_first=True)

## 会社別にモデル構築
results = []
evals = []
forecast_rows = []
latest_month = df_summary["解約年月"].max()
future_month = latest_month + 1 if latest_month % 100 < 12 else ((latest_month // 100 + 1) * 100 + 1)
future_year = future_month // 100
future_month_num = future_month % 100

for company in df_summary["簡易会社名"].unique():
	df_c = df_encoded[df_summary["簡易会社名"] == company].copy()
	X_all = df_c.drop(columns=["簡易会社名", "解約年月", "解約件数"])
	y_all = df_c["解約件数"]

	if len(X_all) > 1:
		model = LinearRegression()
		model.fit(X_all, y_all)

		## 全期間予測
		y_all_pred = np.clip(np.round(model.predict(X_all)), 0, None).astype(int)
		df_c_result = df_summary[df_summary["簡易会社名"] == company].copy()
		df_c_result["予測解約件数"] = y_all_pred
		df_c_result["件数差"] = df_c_result["予測解約件数"] - df_c_result["解約件数"]
		results.extend(df_c_result.to_dict(orient="records"))

		## 精度評価
		mae = mean_absolute_error(y_all, y_all_pred)
		rmse = mean_squared_error(y_all, y_all_pred, squared=False)
		mape = np.mean(np.abs((y_all - y_all_pred) / y_all.replace(0, np.nan))) * 100

		evals.append({
			"簡易会社名": company,
			"MAE": round(mae, 2),
			"RMSE": round(rmse, 2),
			"MAPE(%)": round(mape, 2)
		})

		## 未来予測
		future_features = df_c.iloc[[-1]].copy()
		future_features["年"] = future_year
		future_features["月"] = future_month_num
		future_features["経過月"] += 1
		future_features["経過月2乗"] = future_features["経過月"] ** 2
		future_features = future_features[X_all.columns]
		y_future = int(np.clip(np.round(model.predict(future_features)[0]), 0, None))

		forecast_rows.append({
			"簡易会社名": company,
			"年": future_year,
			"月": future_month_num,
			"予測解約件数": y_future
		})


result_df = pd.DataFrame(results)
eval_df = pd.DataFrame(evals)
forecast_df = pd.DataFrame(forecast_rows)

result_df.to_csv(flp + "会社別_月別_解約件数_予測_vs_実績.csv", encoding="cp932", index=False)
eval_df.to_csv(flp + "会社別_解約予測モデル評価指標.csv", encoding="cp932", index=False)
forecast_df.to_csv(flp + "会社別_未来解約件数予測.csv", encoding="cp932", index=False)

