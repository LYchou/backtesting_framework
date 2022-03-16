# import numpy as np
# import datetime
from . import order

class Parameters:
    def __init__(self):
        pass

class Strategy:

    params = ()

    def __init__(self,**params):
        self.setup_params(params_dict=params)

    # 用來複寫的method
    def initial(self):
        print('initial value = ',self.data_center.value)

    def pre_next(self):
        pass
    
    def next(self):
        # 策略執行
        pass

    def after_next(self):
        pass

    def pre_open(self):
        pass

    def stop(self):
        pass
        # print('final value = ',self.data_center.value)
    
    ##################################################

    def setup_data_center(self,data_center):
        '''引入資料源'''
        self.data_center = data_center
        self.data_center.params = self.params

    ##################################################

    # 給外部使用的下單method

    # 開倉
    def order_open_size(self,ticker,size=1,limit_pending_period=5,additional_info={}):
        order_obj = order.Order(
            data_center=self.data_center,
            ticker=ticker,
            size=size,
            limit_pending_period=limit_pending_period, # 掛單太久都沒有成交的交易日門檻，超過就取消掛單
            additional_info = additional_info
        )
        self.pending_openOrder(order_obj)

    def order_open_value(self,ticker,value,limit_pending_period=5):
        df_px = self.data_center.ticker_dict[ticker]
        px = df_px.loc[self.data_center.date,'CLOSE']
        size = int(value/px) # 無條件捨去小數點
        self.order_open_size(ticker,size)

    # 平倉
    def order_close(self,order_obj):
        self.pending_closeOrder(order_obj)

    def order_close_byMagicNumber(self,magic_number):
        order_obj = self.data_center.get_order_by_magic_number(magic_number)
        self.order_close(order_obj)

    def order_close_byTicker(self,ticker):
        orders = self.data_center.get_orders_by_ticker(ticker)
        for order_obj in orders:
            self.order_close(order_obj)
    
    def AllOrders_close(self):
        for order_obj in self.data_center.holded_orders:
            self.order_close(order_obj)

    # 
    def order_ticker_targetValue(self,ticker,targetValue):
        currentValue = self.data_center.get_HoldedTotalValue_of_ticker(ticker)
        self.order_open_value(ticker, targetValue-currentValue)

    def order_ticker_targetPercent(self,ticker,percent):
        targetValue = self.data_center.value*percent
        self.order_ticker_targetValue(ticker,targetValue)

    # 
    def order_tickers_maintain_equal_weight(self,target_tickers,reserve_ratio):
        '''
        輸入欲維持target_tickers的權重，並輸入保留多少比例的現金reserve_ratio。
        1. 先把持有部位中不屬於target_tickers的先平倉
        2. 調整target_tickers到目標權重(開多單、開空單)
        '''
        # 平倉
        self.__close_tickers_areNot_in_targetList(targetList=target_tickers)
        # 開倉
        percent = (1-reserve_ratio)/len(target_tickers) if len(target_tickers)>0 else 0
        for ticker in target_tickers:
            self.order_ticker_targetPercent(ticker, percent)

    # 
    def order_tickers_equal_weight(self,target_tickers,reserve_ratio):
        '''
        輸入欲等權重買進的target_tickers，並輸入保留多少比例的現金reserve_ratio。
        1. 平倉所有部位
        2. 重新開倉
        '''
        # 平倉
        self.AllOrders_close()
        # 開倉
        percent = (1-reserve_ratio)/len(target_tickers) if len(target_tickers)>0 else 0
        Value = self.data_center.value*percent if percent!=0 else 0
        for ticker in target_tickers:
            self.order_open_value(ticker, Value)

    def order_tickers_self_defined_weight(self,weight_dict,reserve_ratio):
        '''
        先平倉全部，再買進目標自定義權重。
        '''
        # 平倉
        self.AllOrders_close()
        # 開倉
        target_weight_dict = self.distribute_weights(weight_dict,reserve_ratio)
        for ticker in target_weight_dict:
            percent = target_weight_dict[ticker]
            Value = self.data_center.value*percent if percent!=0 else 0
            self.order_open_value(ticker, Value)
        
    def order_tickers_maintain_self_defined_weight(self,weight_dict,reserve_ratio):
        '''
        先把非目標標的平倉，自己再將部位調整到定義權重。
        weight_dict -> ticker:weight

        '''
        target_tickers = list(weight_dict.keys())
        self.__close_tickers_areNot_in_targetList(targetList=target_tickers)

        target_weight_dict = self.distribute_weights(weight_dict,reserve_ratio)
        for ticker in target_weight_dict:
            percent = target_weight_dict[ticker]
            self.order_ticker_targetPercent(ticker, percent)


    # cerebro 會自動呼叫，確定每個股票在最後一個交易日會平倉
    def close_orders_AtTheirLastTradingDay(self):
        '''
        如果明天是這個order的價格最後一天，今天掛出賣單。
        '''
        for order_obj in self.data_center.holded_orders:
            if order_obj.check_tomorrow_is_LastTradingDay_orNot():
                self.order_close(order_obj)




    ##################################################

    def trading(self):
        '''
        先平倉，在開倉。其中順序(先執行現金流入帳戶比較大的單)
        平倉:
            (因關掉金額大的多單，對帳戶是流入最多現金的)
            把執行訂單做排序，先執行最大金額(多單)逐一到最小金額的訂單
        開倉:
            把執行訂單做排序，先執行最小金額(空單)逐一到最大金額的訂單
        
        '''
        
        # 避免重複平倉相同的order
        self.data_center.pending_close_orders = list(set(self.data_center.pending_close_orders))

        # 安排訂單執行順序
        self.arrange_theOrder_of_executeCloseOrders()
        self.arrange_theOrder_of_executeOpenOrders()

        for order_obj in self.data_center.pending_close_orders:
            order_obj.close()

        for order_obj in self.data_center.pending_open_orders:
            order_obj.execute()

        # 判斷我有沒有要輸出交易訊息
        if self.data_center.notify_orNot:
            # 還未刪除交易過的掛單，把那些掛單輸出提示訊息
            # 檢索訂單今天送出訂單
            today_sending_closeOrders = self.data_center.pending_close_orders
            today_sending_openOrders = self.data_center.pending_open_orders
            # 平倉提示訊息
            self.notify_closeOrders(today_sending_closeOrders)
            # 開倉提示訊息
            self.notify_openOrders(today_sending_openOrders)
        
        # 若掛單，持續掛著超過限制時間(order_obj.limit_pending_period)，就取消掛單
        self.cancell_PendingToolong_closeOrders()
        self.cancell_PendingToolong_openOrders()

        # 調整持有掛單。上面程式碼平倉的要移除，開倉的要加進來
        self.adjust_holdedOrders()
        # 調整掛單。已經送出去交易的掛單移除
        self.adjust_pendingOrders()
        
 

    ##
    ## 工具方法
    def setup_params(self,params_dict):
        params_obj = Parameters()
        for Tuple in self.params:
            setattr(params_obj,Tuple[0],Tuple[1])
        for key in params_dict:
            setattr(params_obj,key,params_dict[key])
        self.params = params_obj

    def pending_openOrder(self,order_obj):
        order_obj.pendingOpenOrder_orNot = True
        order_obj.sending_date=self.data_center.date
        self.data_center.pending_open_orders.append(order_obj)
        self.data_center.order_records.append(order_obj)

    def pending_closeOrder(self,order_obj):
        order_obj.pendingCloseOrder_orNot = True
        order_obj.sendingClose_date = self.data_center.date        
        self.data_center.pending_close_orders.append(order_obj)

    def arrange_theOrder_of_executeOpenOrders(self):
        '''
        開倉是按照list順序，由金額小排到大，避免太早margin call
        '''
        self.data_center.pending_open_orders = sorted(
            self.data_center.pending_open_orders,
            key=lambda order_obj:order_obj.calculate_CurrentValue(),
            reverse=False # 小到大
        )
    
    def arrange_theOrder_of_executeCloseOrders(self):
        '''
        開倉是按照list順序，由市值大排到小，避免太早margin call
        '''
        self.data_center.pending_close_orders = sorted(
            self.data_center.pending_close_orders,
            key=lambda order_obj:order_obj.calculate_CurrentValue(),
            reverse=True # 大到小
        )
    

    def notify_closeOrders(self,orders):
        for order_obj in orders:
            order_obj.close_order_notify()

    def notify_openOrders(self,orders):
        for order_obj in orders:
            order_obj.open_order_notify()

    def cancell_PendingToolong_closeOrders(self):
        for order_obj in self.data_center.pending_close_orders:
            if order_obj.calculate_pendingClose_peirod()>order_obj.limit_pending_period:
                order_obj.pendingCloseOrder_orNot = False

    def cancell_PendingToolong_openOrders(self):
        for order_obj in self.data_center.pending_open_orders:
            if order_obj.calculate_pendingOpen_peirod()>order_obj.limit_pending_period:
                order_obj.pendingOpenOrder_orNot = False

    def adjust_holdedOrders(self):
        '''
        附註: 要比 self.adjust_pendingOrders() 先執行，因為會運用到調整前的self.data_center.pending_open_orders
        '''
        # 舊訂單，看看有沒有平倉
        self.data_center.holded_orders = [order_obj for order_obj in self.data_center.holded_orders if order_obj.holdedOrder_orNot]
        # 新訂單，加入
        newOrders = [order_obj for order_obj in self.data_center.pending_open_orders if order_obj.holdedOrder_orNot]
        self.data_center.holded_orders = self.data_center.holded_orders + newOrders
    
    def adjust_pendingOrders(self):
        self.data_center.pending_open_orders = [order_obj for order_obj in self.data_center.pending_open_orders if order_obj.pendingOpenOrder_orNot]
        self.data_center.pending_close_orders = [order_obj for order_obj in self.data_center.pending_close_orders if order_obj.pendingCloseOrder_orNot]


    def __close_tickers_areNot_in_targetList(self,targetList):
        '''
        在持有部位中，找到不屬於targetList做平倉
        '''
        for order_obj in self.data_center.holded_orders:
            if order_obj.ticker not in targetList:
                self.order_close(order_obj)


    def find_tickerList_today_closePrice_available(self):
        tickerList = list(self.data_center.ticker_dict.keys())
        available_tickerList = list(
            filter(
                lambda ticker:self.data_center.check_tickerData_available(ticker, 'CLOSE'),
                tickerList
            )
        )
        return available_tickerList

    def distribute_weights(self,weight_dict,reserve_ratio):
        raw_weights = list(weight_dict.values())
        raw_weights_sum = sum(raw_weights)
        target_weight_dict = dict()
        for ticker in weight_dict:
            raw_weight = weight_dict[ticker]
            target_weight = (raw_weight/raw_weights_sum)*(1-reserve_ratio) # 因為要保留資金，所以做調整
            target_weight_dict[ticker] = target_weight
        return target_weight_dict


    ###########
    # update account

    def update_HoldingTicker_MarketValue(self):
        for ticker in self.data_center.HoldingTicker_MarketValue.columns:
            self.data_center.HoldingTicker_MarketValue.loc[self.data_center.date,ticker] = self.data_center.get_HoldedTotalValue_of_ticker(ticker)

    def update_HoldingTicker_size(self):
        for ticker in self.data_center.HoldingTicker_size.columns:
            self.data_center.HoldingTicker_size.loc[self.data_center.date,ticker] = self.data_center.get_HoldedTotalSize_of_ticker(ticker)

    def update_AccountState(self):
        self.update_HoldingTicker_MarketValue()
        self.update_HoldingTicker_size()
        asset_value = self.data_center.HoldingTicker_MarketValue.loc[self.data_center.date,:].sum()
        cash_value = self.data_center.cash
        self.data_center.value = asset_value+cash_value

    def set_date_forward(self):
        '''日期往前迭代'''
        today_idx = self.data_center.dateList.index(self.data_center.date)
        tomorrow_idx = today_idx+1 
        # 今天非最後一天存入下個交易日，今天是最後一天不更改新的值
        self.data_center.date = self.data_center.dateList[tomorrow_idx] if tomorrow_idx<len(self.data_center.dateList) else self.data_center.date

    
    def save_AccountState(self):
        self.data_center.value_list.append(self.data_center.value)
        self.data_center.cash_list.append(self.data_center.cash)

    


    