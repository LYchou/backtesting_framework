import datetime
import backtesting_framework as bf
import pandas as pd


class Strategy(bf.strategy.Strategy):

    

    params = (
        ('formation_period',20),
        ('stocks_number',2),
        ('reserve_ratio',0.05),
    )

    def initial(self):
        

        # 製作收盤價的df，以便後面計算動能
        px_series_dict = {}
        for ticker in self.data_center.ticker_dict:
            px_series_dict[ticker]= self.data_center.ticker_dict[ticker]['CLOSE']
        px_df = pd.DataFrame(px_series_dict)
        
        # 計算動能
        self.momentum_df = px_df.pct_change(self.params.formation_period)

        # 透過 data_center 找到回測期間月底的時間點
        self.TheEndDates_of_TheseMonths = self.data_center.find_TheEndDates_of_TheseMonths()

    def pre_next(self):

        if self.data_center.notify_orNot:
            
            pending_open_orders = [order_obj.ticker for order_obj in self.data_center.pending_open_orders]
            pending_close_orders = [order_obj.ticker for order_obj in self.data_center.pending_close_orders]
            holded_orders = [order_obj.ticker for order_obj in self.data_center.holded_orders]
            if pending_open_orders==[] and pending_close_orders==[]:
                return

            print('---pre_next---')
            print(f'{self.data_center.date} , cash={self.data_center.cash} , value={self.data_center.value}')
            print('==========')
            print(f'pending_open_orders={pending_open_orders}')
            print(f'pending_close_orders={pending_close_orders}')
            print(f'holded_orders={holded_orders}')


    def next(self):
        
        # 月底計算動能，隔天月初開盤調整部位
        if self.data_center.date in self.TheEndDates_of_TheseMonths:
            self.rebalance()



    def after_next(self):

        if self.data_center.notify_orNot:
            
            pending_open_orders = [order_obj.ticker for order_obj in self.data_center.pending_open_orders]
            pending_close_orders = [order_obj.ticker for order_obj in self.data_center.pending_close_orders]
            holded_orders = [order_obj.ticker for order_obj in self.data_center.holded_orders]
            if pending_open_orders==[] and pending_close_orders==[]:
                return
            print('---after_next---')
            print(f'pending_open_orders={pending_open_orders}')
            print(f'pending_close_orders={pending_close_orders}')
            print(f'holded_orders={holded_orders}')
            print('\n\n')


    def rebalance(self):

        today = self.data_center.date

        momentum = self.momentum_df.loc[today,:].sort_values(ascending=False)
        target_tickers = momentum.index[:self.params.stocks_number]

        self.order_tickers_maintain_equal_weight(
            target_tickers=target_tickers,
            reserve_ratio=self.params.reserve_ratio
        )

        if self.data_center.notify_orNot:
            # print_out
            for ticker in target_tickers:
                rank = list(momentum.index).index(ticker)+1
                momentum_value = momentum[ticker]

                print(f'{ticker} - rank:{rank} - momentum_value:{momentum_value}')
