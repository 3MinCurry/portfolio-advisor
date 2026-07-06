"""
Market data functions using polygon.io for fetching real-time prices.
"""

import logging
from typing import Set
from prices import get_share_price

logger = logging.getLogger()

# Reject Polygon/tag noise that would slash portfolio value (e.g. SPY at $36).
_MAX_PRICE_SWING_RATIO = 0.5


def _price_update_is_sane(existing: float, new_price: float) -> bool:
    if new_price <= 0:
        return False
    if existing <= 0:
        return True
    ratio = new_price / existing
    return _MAX_PRICE_SWING_RATIO <= ratio <= (1 / _MAX_PRICE_SWING_RATIO)


def update_instrument_prices(job_id: str, db) -> None:
    """
    Fetch current prices for all instruments in the user's portfolio using polygon.io.
    Updates the instruments table with current prices.

    Args:
        job_id: The job ID to identify the user's portfolio
        db: Database instance
    """
    try:
        logger.info(f"Market: Fetching current prices for job {job_id}")

        # Get the job to find the user
        job = db.jobs.find_by_id(job_id)
        if not job:
            logger.error(f"Market: Job {job_id} not found")
            return

        user_id = job['clerk_user_id']

        # Get all unique symbols from user's positions
        accounts = db.accounts.find_by_user(user_id)
        symbols = set()

        for account in accounts:
            positions = db.positions.find_by_account(account['id'])
            for position in positions:
                symbols.add(position['symbol'])

        if not symbols:
            logger.info("Market: No symbols to update prices for")
            return

        logger.info(f"Market: Fetching prices for {len(symbols)} symbols: {symbols}")

        # Update prices for each symbol
        update_prices_for_symbols(symbols, db)

        logger.info("Market: Price update complete")

    except Exception as e:
        logger.error(f"Market: Error updating instrument prices: {e}")
        # Non-critical error, continue with analysis


def update_prices_for_symbols(symbols: Set[str], db) -> None:
    """
    Fetch and update prices for a set of symbols using polygon.io.

    Args:
        symbols: Set of ticker symbols to update
        db: Database instance
    """
    if not symbols:
        logger.info("Market: No symbols to update")
        return

    symbols_list = list(symbols)
    price_map = {}

    # Fetch price for each symbol using polygon.io (keep DB price if lookup fails)
    for symbol in symbols_list:
        try:
            instrument = db.instruments.find_by_symbol(symbol)
            existing = float(instrument.get("current_price") or 0) if instrument else 0.0
            price = get_share_price(symbol, fallback=existing)
            if price > 0 and _price_update_is_sane(existing, price):
                price_map[symbol] = price
                logger.info(f"Market: Retrieved {symbol} price: ${price:.2f}")
            elif price > 0:
                logger.warning(
                    f"Market: Ignoring suspicious {symbol} price ${price:.2f} "
                    f"(existing ${existing:.2f})"
                )
            else:
                logger.warning(f"Market: No price available for {symbol}")
        except Exception as e:
            logger.warning(f"Market: Could not fetch price for {symbol}: {e}")

    logger.info(f"Market: Retrieved prices for {len(price_map)}/{len(symbols_list)} symbols")

    # Update database with fetched prices (global instruments table — shared across users)
    for symbol, price in price_map.items():
        try:
            instrument = db.instruments.find_by_symbol(symbol)
            if instrument:
                update_data = {'current_price': price}
                success = db.client.update(
                    'instruments',
                    update_data,
                    "symbol = :symbol",
                    {'symbol': symbol}
                )
                if success:
                    logger.info(f"Market: Updated {symbol} price to ${price:.2f}")
                else:
                    logger.warning(f"Market: Failed to update price for {symbol}")
            else:
                logger.warning(f"Market: Instrument {symbol} not found in database")
        except Exception as e:
            logger.error(f"Market: Error updating {symbol} in database: {e}")

    # Log symbols that didn't get prices
    missing = set(symbols_list) - set(price_map.keys())
    if missing:
        logger.warning(f"Market: No prices found for: {missing}")


def get_all_portfolio_symbols(db) -> Set[str]:
    """
    Get all unique symbols across all users' portfolios.
    Useful for pre-fetching prices in batch operations.

    Args:
        db: Database instance

    Returns:
        Set of unique ticker symbols
    """
    symbols = set()

    try:
        rows = db.query_raw("SELECT DISTINCT symbol FROM positions WHERE symbol IS NOT NULL")

        for row in rows:
            symbol = row.get("symbol")
            if symbol:
                symbols.add(symbol)

    except Exception as e:
        logger.error(f"Market: Error fetching all symbols: {e}")

    return symbols