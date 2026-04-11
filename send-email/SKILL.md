---
name: send-email
description: 浣跨敤鏈満 Python 鑴氭湰閫氳繃 QQ SMTP 鍙戦€侀偖浠讹紝鏀寔绾枃鏈€丠TML 鍜岄檮浠躲€?allowedTools:
  - Bash(*)
---

# send-email

杩欎釜 skill 鐢ㄤ簬閫氳繃鏈満 Python 鑴氭湰鍙戦€侀偖浠躲€?
鑴氭湰璺緞锛歚send_email.py`

## 浣曟椂浣跨敤

- 鐢ㄦ埛鏄庣‘瑕佹眰鈥滃彂閭欢鈥濃€滃彂閫侀偖浠垛€濃€滈偖浠堕€氱煡鈥濃€滄妸杩欐鍐呭鍙戝埌閭鈥濄€?- 宸茬粡鍏峰鏀朵欢浜恒€佷富棰橈紝浠ュ強姝ｆ枃鎴栧彲鐢变笂涓嬫枃鍙潬璧疯崏鐨勬鏂囥€?- 闇€瑕佸彂閫佺函鏂囨湰銆丠TML 閭欢鎴栧甫闄勪欢鐨勯偖浠躲€?
## 琛屼负瑙勫垯

- 褰撶敤鎴锋槑纭姹傚彂閫侀偖浠朵笖蹇呰淇℃伅瀹屾暣鏃讹紝鍙互**鐩存帴鍙戦€?*锛屾棤闇€棰濆纭銆?- 榛樿鏀朵欢閭鏄?`3972766883@qq.com`銆傚鏋滅敤鎴锋病鏈夌壒鍒鏄庢敹浠朵汉锛屽氨浣跨敤杩欎釜閭浣滀负榛樿鏀朵欢鍦板潃銆?- 濡傛灉缂哄皯涓婚锛屾垨姝ｆ枃鍐呭鏃犳硶浠庝笂涓嬫枃鍙潬鐢熸垚锛屽厛鍚戠敤鎴疯ˉ闂己澶变俊鎭€?- 鍙互浠ｅ啓閭欢鍐呭锛屼絾**涓嶈缂栭€犱簨瀹炪€佹椂闂淬€佹壙璇恒€佹姤浠枫€侀檮浠跺唴瀹规垨鏀朵欢浜轰俊鎭?*銆?- 濡傛灉鐢ㄦ埛瑕佸彂 HTML 閭欢锛屼紭鍏堝悓鏃舵彁渚?`text_body` 浣滀负绾枃鏈洖閫€锛涘鏋滄病鏈夛紝鑴氭湰浼氳嚜鍔ㄨˉ涓€涓畝鐭殑绾枃鏈洖閫€姝ｆ枃锛屽啀闄勪笂 HTML 姝ｆ枃銆?- 闄勪欢璺緞蹇呴』鏄?*缁濆璺緞**銆傚鏋滈檮浠朵笉瀛樺湪锛屼笉瑕佺户缁彂閫侊紝鐩存帴杩斿洖閿欒銆?
## 鐜鍙橀噺

鑴氭湰浠庣幆澧冨彉閲忚鍙?SMTP 閰嶇疆锛?
- `OPENCODE_EMAIL_SMTP_HOST`
- `OPENCODE_EMAIL_SMTP_PORT`
- `OPENCODE_EMAIL_SMTP_USERNAME`
- `OPENCODE_EMAIL_SMTP_PASSWORD`

绔彛寤鸿浣跨敤锛?
- `465`锛氱洿鎺ヤ娇鐢?SSL锛圦Q 閭鎺ㄨ崘锛?- 鍏朵粬绔彛锛氳姹傛湇鍔″櫒鏀寔 STARTTLS

## 鑷鍛戒护

```powershell
python ".\send_email.py" --validate-config
```

## 鎺ㄨ崘璋冪敤鏂瑰紡

浣跨敤 PowerShell 瀵硅薄杞?JSON锛屽啀閫氳繃 stdin 浼犵粰鑴氭湰锛岄伩鍏嶆鏂囧拰 HTML 鐨勮浆涔夐棶棰樸€?
鍦?Windows PowerShell 涓紝鍙戦€佸寘鍚腑鏂囨垨澶嶆潅 HTML 鐨勯偖浠跺墠锛屽缓璁厛鏄惧紡鍒囨崲鍒?UTF-8锛?
```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## 杈撳叆绾﹀畾

stdin JSON 鏀寔杩欎簺瀛楁锛?
- `to`: 瀛楃涓叉垨瀛楃涓叉暟缁?- `subject`: 瀛楃涓?- `text_body`: 瀛楃涓诧紝鍙€?- `html_body`: 瀛楃涓诧紝鍙€?- `attachments`: 瀛楃涓叉暟缁勶紝鍙€夛紝蹇呴』涓虹粷瀵硅矾寰?
鍏朵腑 `text_body` 鍜?`html_body` 鑷冲皯瑕佹彁渚涗竴涓€?