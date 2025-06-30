import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Google Sheets setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "/etc/secrets/gcp_credentials.json"
SPREADSHEET_NAME = "GastosMensualesJC"

REINTEGRO_TOPES = {
    "Supermercado": 400000,
    "Combustible": 400000,
    "Tienda": 400000,
    "Bares": 400000,
    "Pagopar": 400000,
    "Monchis": 160000
}

def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

def append_row(tipo, categoria, monto):
    sheet = get_sheet()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, tipo, categoria, str(monto)])

def calcular_total_reintegro_categoria(categoria):
    sheet = get_sheet()
    rows = sheet.get_all_records()
    return sum(int(row["Monto"]) for row in rows if row["Tipo"] == "Reintegros" and row["Categoría"] == categoria)

def registrar_reintegro_automatico(categoria, monto_solicitado):
    if categoria not in REINTEGRO_TOPES:
        return "Categoría no válida para reintegro."

    total_actual = calcular_total_reintegro_categoria(categoria)
    disponible = REINTEGRO_TOPES[categoria] - total_actual

    if disponible <= 0:
        return f"Tope mensual alcanzado para {categoria}. No se registró reintegro."

    monto_reintegro = min(monto_solicitado, disponible)
    append_row("Reintegros", categoria, monto_reintegro)
    return f"Reintegro automático registrado: {categoria} - {monto_reintegro}"

async def ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria, monto = " ".join(context.args).split(":")
        append_row("Ingresos", categoria.strip(), int(monto.strip()))
        await update.message.reply_text("Ingreso registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /ingreso Categoria: Monto")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria, monto = " ".join(context.args).split(":")
        categoria = categoria.strip()
        monto = int(monto.strip())
        append_row("Gastos", categoria, monto)

        mensaje = "Gasto registrado."
        if categoria in REINTEGRO_TOPES:
            reintegro_40 = int(monto * 0.4)
            resultado = registrar_reintegro_automatico(categoria, reintegro_40)
            mensaje += f"\n{resultado}"

        await update.message.reply_text(mensaje)
    except:
        await update.message.reply_text("Formato incorrecto. Usa /gasto Categoria: Monto")

async def reintegro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria, monto = " ".join(context.args).split(":")
        categoria = categoria.strip()
        monto = int(monto.strip())
        resultado = registrar_reintegro_automatico(categoria, monto)
        await update.message.reply_text(resultado)
    except:
        await update.message.reply_text("Formato incorrecto. Usa /reintegro Categoria: Monto")

async def informe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        args = context.args
        now = datetime.datetime.now()
        current_month = now.month
        current_year = now.year

        if args and args[0].lower() == "gastos":
            resumen = {}
            total = 0
            for row in rows:
                if row["Tipo"] == "Gastos":
                    cat = row["Categoría"]
                    monto = int(row["Monto"])
                    resumen[cat] = resumen.get(cat, 0) + monto
                    total += monto
            lines = ["GASTOS:"]
            for cat, monto in resumen.items():
                lines.append(f"  {cat}: {monto}")
            lines.append(f"\nTOTAL GASTOS: {total}")
            await update.message.reply_text("\n".join(lines))
            return

        if args and args[0].lower() == "reintegros":
            resumen = {}
            for row in rows:
                fecha_str = row["Fecha"]
                try:
                    fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                except:
                    continue
                if row["Tipo"] == "Reintegros" and fecha.month == current_month and fecha.year == current_year:
                    cat = row["Categoría"]
                    monto = int(row["Monto"])
                    resumen[cat] = resumen.get(cat, 0) + monto
            lines = ["REINTEGROS DISPONIBLES:"]
            for cat in REINTEGRO_TOPES:
                usado = resumen.get(cat, 0)
                restante = max(REINTEGRO_TOPES[cat] - usado, 0)
                disponible_para_gastar = int(restante / 0.4) if restante > 0 else 0
                lines.append(f"  {cat}: {disponible_para_gastar}")
            await update.message.reply_text("\n".join(lines))
            return

        # Informe general
        activo = 0
        resumen = {"Ingresos": {}, "Gastos": {}, "Reintegros": {}}
        totales = {"Ingresos": 0, "Gastos": 0, "Reintegros": 0}

        for row in rows:
            tipo = row["Tipo"]
            categoria = row["Categoría"]
            try:
                monto = int(row["Monto"])
            except:
                continue

            if tipo == "Ingresos":
                activo += monto
            elif tipo == "Gastos":
                activo -= monto
            elif tipo == "Reintegros":
                activo += monto

            if categoria not in resumen[tipo]:
                resumen[tipo][categoria] = 0
            resumen[tipo][categoria] += monto
            totales[tipo] += monto

        lines = [f"ACTIVO: {activo}\n"]
        for tipo in ["Ingresos", "Gastos", "Reintegros"]:
            lines.append(f"{tipo}:")
            for cat, monto in resumen[tipo].items():
                lines.append(f"  {cat}: {monto}")
            lines.append(f"TOTAL {tipo.upper()}: {totales[tipo]}\n")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text("Error al generar el informe.")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("ingreso", ingreso))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("reintegro", reintegro))
    app.add_handler(CommandHandler("informe", informe))
    app.run_polling()
