-- Minimal compatible subset of a Freqtrade trades table.
-- No account records are included. open_date/close_date are UTC timestamps.
-- close_profit is a ratio (0.01 = 1%); close_profit_abs is quote-currency PnL.
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    pair TEXT NOT NULL,
    is_open INTEGER NOT NULL CHECK (is_open IN (0, 1)),
    open_date TEXT NOT NULL,
    close_date TEXT,
    close_profit REAL,
    close_profit_abs REAL,
    is_short INTEGER NOT NULL CHECK (is_short IN (0, 1))
);
