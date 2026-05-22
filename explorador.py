import asyncio
import aiohttp
import logging
import random
import sqlite3
import requests
import yfinance as yf
from config import get_settings
from database import Database
from models import RawMarketData
from fundamental_filter import FundamentalFilter
from datetime import datetime, timezone
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("ExploradorSEC")

def verificar_margen_yfinance(ticker):
    """Consulta a Yahoo Finance con disfraz y detector de baneos."""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        stock = yf.Ticker(ticker, session=session)
        info = stock.info
        
        if not info or 'symbol' not in info:
            return 0.0
            
        gross_margin = info.get('grossMargins', 0)
        return float(gross_margin) if gross_margin else 0.0
        
    except Exception as e:
        error_msg = str(e)
        # SENSOR DE BANEO: Si Yahoo nos bloquea, devolvemos -1.0
        if "Too Many Requests" in error_msg or "Rate limited" in error_msg:
            return -1.0
        
        log.warning(f"⚠️ Error normal en YFinance para {ticker}: {error_msg}")
        return 0.0

async def minero_autonomo():
    settings = get_settings()
    db = Database(settings.database_path)
    await db.initialize()

    headers = {"User-Agent": settings.sec_user_agent}
    filtro_fundamental = FundamentalFilter(
        settings.margen_bruto_minimo,
        settings.eps_years_lookback,
        settings.shares_years_lookback
    )

    log.info("Iniciando Motor de Descubrimiento Híbrido SEC + YFinance 24/7...")

    while True:
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get("https://www.sec.gov/files/company_tickers.json") as resp:
                    if resp.status != 200:
                        log.error("No se pudo descargar la lista de la SEC. Esperando 10 min...")
                        await asyncio.sleep(600)
                        continue
                    mercado_total = await resp.json()

                tickers_list = list(mercado_total.values())
                random.shuffle(tickers_list)
                lote = tickers_list[:10]

                for data in lote:
                    ticker = data["ticker"]
                    cik = str(data["cik_str"]).zfill(10)

                    log.info(f"--- Análisis Híbrido: {ticker} ---")

                    margen_yf = await asyncio.to_thread(verificar_margen_yfinance, ticker)

                    # --- NUEVA LÓGICA DE SUPERVIVENCIA ---
                    if margen_yf == -1.0:
                        log.warning("🛑 YFinance nos dio un Time-Out (Límite alcanzado).")
                        log.warning("💤 El Minero dormirá por 15 minutos para enfriar la IP...")
                        await asyncio.sleep(900) # 900 segundos = 15 minutos
                        continue # Pasa a la siguiente empresa después de despertar
                    # --------------------------------------

                    # Tu regla estricta del 50% mínimo para empresas tecnológicas
                    if margen_yf < 0.50:
                        log.info(f"❌ Descartado por YFinance (Margen: {margen_yf*100:.1f}%)")
                        await asyncio.sleep(2.5) # Un poco más lento para evitar enojar a Yahoo
                        continue

                    log.info(f"💎 {ticker} pasó filtro YFinance (Margen: {margen_yf*100:.1f}%). Consultando SEC...")

                    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                    async with session.get(facts_url) as facts_resp:
                        if facts_resp.status == 429:
                            log.warning("Límite SEC alcanzado. Durmiendo 10 min.")
                            await asyncio.sleep(600)
                            continue
                        elif facts_resp.status != 200:
                            await asyncio.sleep(1.5)
                            continue

                        company_facts = await facts_resp.json()

                        raw_mock = RawMarketData(
                            ticker=ticker,
                            sec_facts=company_facts,
                            history=pd.DataFrame(),
                            fetched_at=datetime.now(tz=timezone.utc)
                        )

                        resultado, snap = filtro_fundamental.evaluate(raw_mock)

                        if resultado.passed:
                            log.info(f"🚀 ¡DESCUBRIMIENTO TOTAL! {ticker} aprobado por SEC.")
                            
                            try:
                                conn = sqlite3.connect("data/arquitecto.db", timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("CREATE TABLE IF NOT EXISTS descubrimientos (ticker TEXT UNIQUE, fecha TEXT)")
                                cursor.execute("INSERT OR IGNORE INTO descubrimientos (ticker, fecha) VALUES (?, ?)", (ticker, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                conn.commit()
                                conn.close()
                                log.info(f"💾 {ticker} guardado en la DB del Arquitecto.")
                            except Exception as e:
                                log.error(f"Error guardando en DB: {e}")
                            
                        else:
                            log.info(f"Descartado por SEC: {resultado.reasons[0] if resultado.reasons else 'No apto'}")

                    await asyncio.sleep(2.5)

            log.info("Lote de 10 completado. Descansando 2 minutos antes del siguiente lote...")
            await asyncio.sleep(120)

        except Exception as e:
            log.error(f"Error crítico en el minero: {e}. Reiniciando en 60s...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(minero_autonomo())
    except KeyboardInterrupt:
        log.info("Motor de exploración detenido por el usuario.")
