
# region imports
from AlgorithmImports import *
# endregion

import clr
import math
import heapq
from itertools import groupby
from decimal import Decimal

class OrderImbalanceAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2013, 10, 7)
        self.SetEndDate(2013, 10, 7)
        self.SetCash(1000000)

        self.symbol = self.AddEquity("SPY", Resolution.Tick, Market.USA, True, 0, True).Symbol

        self.level_count = 5  # Number of order book levels to monitor
        self.weights = [math.exp(-i) for i in range(self.level_count)]
        self.tick_count = 0
        self.bid_orders = []
        self.ask_orders = []

        self.imbalance_threshold = 0.2

        # Schedule the plotting method to run every 5 minutes
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), self.TimeRules.Every(timedelta(minutes=5)), self.PlotData)

    def OnData(self, data):
        if self.tick_count < 300000:
            for tick in data.Ticks[self.symbol]:
                if tick.TickType == TickType.Trade:
                    self.ProcessTradeTick(tick)
                elif tick.TickType == TickType.Quote:
                    self.ProcessQuoteTick(tick)

            self.tick_count += 1

    def ProcessTradeTick(self, tick):
        # Update order book for trade ticks
        if self.bid_orders and self.ask_orders:
            if tick.Price in [-order[0] for order in self.bid_orders]:
                order = [[tick.Price, tick.Quantity, 1]]  # 1 for ask
                self.bid_orders, self.ask_orders = self.UpdateOrderBook(order, self.bid_orders, self.ask_orders)
            elif tick.Price in [order[0] for order in self.ask_orders]:
                order = [[tick.Price, tick.Quantity, 0]]  # 0 for bid
                self.bid_orders, self.ask_orders = self.UpdateOrderBook(order, self.bid_orders, self.ask_orders)

    def ProcessQuoteTick(self, tick):
        # Update order book for quote ticks
        if tick.AskPrice > 1:
            order = [[tick.AskPrice, tick.AskSize, 1]]  # 1 for ask
        else:
            order = [[tick.BidPrice, tick.BidSize, 0]]  # 0 for bid

        self.bid_orders, self.ask_orders = self.UpdateOrderBook(order, self.bid_orders, self.ask_orders)

    def PlotData(self):
        if self.bid_orders and self.ask_orders and 8 < self.Time.hour < 14:
            self.Log(f"Current Time: {self.Time}")

            # Plot order book prices
            self.Plot("Price", "Bid Level 2", -self.bid_orders[1][0]) # Second highest bid price
            self.Plot("Price", "Bid Level 1", -self.bid_orders[0][0]) # Highest bid price
            self.Plot("Price", "Ask Level 1", self.ask_orders[0][0])
            self.Plot("Price", "Ask Level 2", self.ask_orders[1][0])
            mid_price = (-self.bid_orders[0][0] + self.ask_orders[0][0]) / 2
            self.Plot("Price", "MidPrice", mid_price)

            # Calculate imbalance ratio
            bid_summary = [[-round(order[0], 2), int(round(order[1]))] for order in self.bid_orders]
            ask_summary = [[round(order[0], 2), int(round(order[1]))] for order in self.ask_orders]
            bid_volume = sum(vol * weight for (_, vol), weight in zip(bid_summary[:self.level_count], self.weights))
            ask_volume = sum(vol * weight for (_, vol), weight in zip(ask_summary[:self.level_count], self.weights))
            imbalance_ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            self.Plot("Imbalance Ratio", "Value", imbalance_ratio)

            self.Log(f"Bid Levels: {bid_summary[::-1]}, Ask Levels: {ask_summary[:self.level_count]}")

            # Check if the imbalance ratio exceeds the threshold for a buy or sell
            current_holdings = self.Portfolio[self.symbol].Quantity

            # Trigger a buy if imbalance ratio exceeds the positive threshold
            if imbalance_ratio > self.imbalance_threshold:
                if current_holdings >= 0:
                    self.Log(f"Imbalance ratio of {imbalance_ratio} exceeds threshold ({self.imbalance_threshold}), buying full position.")
                    self.SetHoldings(self.symbol, 1)  # Full position on buy
                else:
                    self.Log(f"Imbalance ratio of {imbalance_ratio} exceeds threshold, but already in a short position. Closing short.")
                    self.SetHoldings(self.symbol, 0)  # Close short before going long

            # Trigger a sell if imbalance ratio exceeds the negative threshold
            elif imbalance_ratio < -self.imbalance_threshold:
                if current_holdings <= 0:
                    self.Log(f"Imbalance ratio of {imbalance_ratio} below negative threshold ({-self.imbalance_threshold}), selling full position.")
                    self.SetHoldings(self.symbol, -1)  # Full position on sell
                else:
                    self.Log(f"Imbalance ratio of {imbalance_ratio} below threshold, but already in a long position. Closing long.")
                    self.SetHoldings(self.symbol, 0)  # Close long before going short

            else:
                self.Log(f"Imbalance ratio of {imbalance_ratio} within threshold range. No action taken.")


        if self.Time.hour > 14:
            self.Quit()

    def UpdateOrderBook(self, new_orders, bid_orders, ask_orders):
        for price, volume, order_type in new_orders:
            remaining_volume = volume

            if order_type == 0:  # Buy order
                while remaining_volume > 0 and ask_orders:
                    ask_price, ask_volume = heapq.heappop(ask_orders)
                    if ask_price > price:
                        heapq.heappush(ask_orders, [ask_price, ask_volume])
                        break
                    if ask_volume <= remaining_volume:
                        remaining_volume -= ask_volume
                    else:
                        heapq.heappush(ask_orders, [ask_price, ask_volume - remaining_volume])
                        remaining_volume = 0
                if remaining_volume > 0:
                    heapq.heappush(bid_orders, [-price, remaining_volume])
            else:  # Sell order
                while remaining_volume > 0 and bid_orders:
                    bid_price, bid_volume = heapq.heappop(bid_orders)
                    if -bid_price < price:
                        heapq.heappush(bid_orders, [bid_price, bid_volume])
                        break
                    if bid_volume <= remaining_volume:
                        remaining_volume -= bid_volume
                    else:
                        heapq.heappush(bid_orders, [bid_price, bid_volume - remaining_volume])
                        remaining_volume = 0
                if remaining_volume > 0:
                    heapq.heappush(ask_orders, [price, remaining_volume])

        # Consolidate order book
        bid_orders = [[price, sum(volume for _, volume in group)] for price, group in groupby(sorted(bid_orders), key=lambda x: x[0])]
        ask_orders = [[price, sum(volume for _, volume in group)] for price, group in groupby(sorted(ask_orders), key=lambda x: x[0])]
        return bid_orders, ask_orders
