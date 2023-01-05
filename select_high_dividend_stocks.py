from cmath import nan
from re import S
import pandas as pd
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from time import sleep
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import re
import numpy as np

chrome_path = "/Users/atsumunagata/chromedriver"
Page_Max = 20


# ドライバーの準備
def get_driver():
    # ヘッドレスモードでブラウザを起動
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
 
    # ブラウザーを起動
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
 
    return driver

# 現在のページからhtmlを取得
def get_source_from_page(driver, page):
    try:
        # ドライバーにターゲットページを渡す
        driver.get(page)
        driver.implicitly_wait(10)  # 見つからないときは、10秒まで待つ
        # 対象ページのhtmlを取得
        page_source = driver.page_source
 
        return page_source
 
    except Exception as e:
 
        return None

# yahooファイナンスから必要な情報を取得
def get_com_info(soup):
    com_list = []
    # trタグを全て取得
    trs = soup.find_all('tr', class_='WRru9z7J')
    
    for tr in trs:
        try:
            com_name = tr.find('a').text
            com_code = tr.find('li').text
            com_price = tr.find('span', class_='_1fofaCjs _2aohzPlv _3uM9p7Zj').text
            # listに必要な情報をリストにまとめ要素として追加
            com_list.append([com_name, com_code, com_price])
            

        except  AttributeError:
            print('attributeerror')
        
        except:
            print('何かしらのエラー（yahoo）')

        
    return com_list

# ir_bankから各企業の決算まとめページの取得
def get_data_url(ir_url, com_code): 

    # irbankのhtmlの取得
    res_ir = requests.get(ir_url + '/'+ com_code, timeout=3.5)
    # beautifulsoupでhtmlを分析
    soup_ir = BeautifulSoup(res_ir.text, 'html.parser')
    
    # css_selecterで決算まとめのurlを取得する
    elem = soup_ir.select('#c_Link > div > div > div > ul:nth-child(4) > li:nth-child(1) > a')
    get_url = elem[0].attrs['href']

    #取得したurlを返り値として戻す
    return get_url
    
   


# 取得したデータフレームを編集する
def df_edit(stock_tables, com_list, geturl_flag):
    # 決算情報がない企業があるため、例外処理を行う
    try:
        if geturl_flag == True:
            # 年度をindexに指定し一つにまとめる
            table_1 = stock_tables[0].set_index('年度')
            table_2 = stock_tables[1].set_index('年度')
            table_3 = stock_tables[2].set_index('年度')
            table_4 = stock_tables[3].set_index('年度')

            df = pd.concat([table_1, table_2, table_3, table_4], axis = 1)

            # 年度の中にある不要な行を削除
            for index_name in df.index.values:
                if re.search('予', index_name) or re.search('年度', index_name):
                    df = df.drop(index = index_name)
            # 最終行にnanがある場合は最終行を省く
            if df.tail(1).isnull().values.sum() != 0:
                df = df[:-1]

            # 編集したデータフレームを保存
            re_data = df.copy()

            # 各要素に含まれる不要な文字を削除
            for index in range(len(df)):
                for column in range(len(df.columns)):
                    if type(df.iat[index, column]) is str:
                        df.iat[index, column] = df.iat[index, column].replace('兆', '').replace('億', '').replace('百万', '').replace('*', '')
            # flagを立てる
            flag = True
            return df, re_data, flag
        
        else:
            flag = False
            return None, None, flag

    # リストエラーの場合flagを下ろす
    except IndexError:
        print(com_list[0])
        print('リストに関するエラー（データ取得時）')
        flag = False
        return None, None, flag

    # その他エラーの場合もflagを下ろす
    except:
        print(com_list[0])
        print('何かしらのエラー（データ取得時）')
        flag = False
        return None, None, flag

def select_stocks(flag, df, com_list):
    try:
        if flag == True:
            # 行数を取得
            index_num = len(df)
            # 株価をint型に変更する
            stock_price = int(com_list[2].replace(',', ''))
            # 最終行の各値を取得
            profit_ratio = float(df['営利率'][index_num - 1])
            capital_ratio = float(df['自己資本比率'][index_num - 1])
            payout_ratio = float(df['配当性向'][index_num - 1])
            per = stock_price/float(df['EPS'][index_num - 1])
            roe = float(df['ROE'][index_num - 1])
            
            print(f'営利率:{profit_ratio}, 自己資本比率:{capital_ratio}, 配当性向:{payout_ratio}, PER:{per}, ROE:{roe}')
            if profit_ratio > target_profit_ratio and capital_ratio > target_capital_ratio and\
                payout_ratio < target_payout_ratio and per <target_per_upper and per > target_per_lower and roe > target_roe:
                # 相関係数の計算 -の除外と、連番の作成
            
                if df['営利'].dtype == object:
                    df_profit = df[~df['営利'].str.contains('-')]['営利'].astype('float').reset_index()
                else:
                    df_profit = df['営利'].astype('float').reset_index()
            

                if df['EPS'].dtype == object:
                    df_eps = df[~df['EPS'].str.contains('-')]['EPS'].astype('float').reset_index()
                else:
                    df_eps = df['EPS'].astype('float').reset_index()

                x_profit = pd.Series(np.arange(1, len(df_profit) + 1))
                x_eps = pd.Series(np.arange(1, len(df_profit) + 1))
                 
                # それぞれの指標と連番を連結
                profit = pd.concat([x_profit, df_profit], axis = 1)
                eps = pd.concat([x_eps, df_eps], axis = 1)
                
                # 相関係数の計算
                profit_corr = profit.corr().iat[0, 1]
                eps_corr = eps.corr().iat[0, 1]

                print(f'営利:{profit_corr}, EPS:{eps_corr}')
                if profit_corr > target_profit and eps_corr > target_eps:
                    re_data.to_csv(f'/Users/atsumunagata/Desktop/プログラミング用/select_stock/{com_list[0]}_{com_list[1]}.csv')


    except ValueError:
        print('valueエラーが発生しています(選定処理内)')
    
    except:
        print('何かしらのエラーが発生しています。(選定処理内)')




if __name__ == "__main__":
    target_per_upper = 15 # per上限
    target_per_lower = 4 # per下限
    target_profit_ratio = 8 # 営利率
    target_payout_ratio = 60 # 配当性向
    target_roe = 8 # ROE
    target_capital_ratio = 40 # 自己資本比率
    target_profit = 0.7 # 営利の相関係数
    target_eps = 0.7 # epsの相関係数
    #yahooファイナンス配当利回りランキングのurl
    yahoo_page = 'https://finance.yahoo.co.jp/stocks/ranking/dividendYield?market=all&term=daily&page=1'
    # ブラウザのdriver取得
    driver = get_driver()

    # 対象ページのurlを取得
    source = get_source_from_page(driver, yahoo_page)
    # リストの作成
    com_lists = []

    # 情報の取得
    for page in range(Page_Max):
        # ページの解析
        soup = BeautifulSoup(source, "html.parser")
        # 一ページの会社情報をリストに追加
        com_lists.extend(get_com_info(soup))
        # 次のページへ遷移
        button = driver.find_element_by_xpath('//*[@id="pagerbtm"]/ul/li[7]/button')
        button.click()
        current_page = driver.current_url
        sleep(1)
        source = get_source_from_page(driver, current_page)
        # 進捗状況の確認
        progress = int((page + 1) / Page_Max *100)
        print(str(progress) + "%")
        sleep(1)
    print('証券コードの取得が完了しました。')
    counter = 1
    counter_max = len(com_lists)
    for com_list in com_lists:
        # irbankのurl
        ir_url = 'https://irbank.net'
        com_code = str(com_list[1])

        # 決算ページの取得
        try:
            get_url = get_data_url(ir_url, com_code)
            sleep(2)
            # 決算ページのtbタグの情報をデータフレームとして取得
            stock_tables = pd.read_html(ir_url + get_url)
            geturl_flag = True

        except:
            print('ページ取得に失敗しました')
            geturl_flag = False

        
        # データフレームの編集
        df, re_data, flag = df_edit(stock_tables, com_list, geturl_flag)
        # flagが立った場合、選定処理に入る            
        select_stocks(flag, df, com_list)

        prog_ratio = float(counter/counter_max*100)
        print(com_list[0]+ ' _ ' + com_list[1] + ' _ ' + str(prog_ratio) + '%' )

        counter += 1
        sleep(1)
    