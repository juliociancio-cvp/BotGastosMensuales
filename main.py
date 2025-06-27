import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Google Sheets setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "/etc/secrets/gcp_credentials.json"  # Ruta del archivo secreto en Render
SPREADSHEET_NAME = "GastosMensualesJC"

# Categorías válidas para reintegros y su tope
REINTEGRO_TOPES = {
    "Supermercado": 400000,
    "Combustible": 400000,
    "Tienda": 400000,
    "Bares": 400000,
    "Pagopar": 400000
}

# Autenticación con Google Sheets
def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

# Agregar una fila a la hoja
def append_row(tipo, categoria, monto):
    sheet = get_sheet()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, tipo, categoria, str(monto)])

# Calcular el ACTIVO y totales por categoría
def generar_informe():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    activo = 0
    resumen = {"Ingresos": {}, "Gastos": {}, "Reintegros": {}}

    for row in rows:
        tipo = row["Tipo"]
        categoria = row["Categoría"]
        monto = int(row["Monto"])
        if tipo == "Ingresos":
            activo += monto
        elif tipo == "Gastos":
            activo -= monto
        elif tipo == "Reintegros":
            activo += monto

        if categoria not in resumen[tipo]:
            resumen[tipo][categoria] = 0
        resumen[tipo][categoria] += monto

    lines = [f"ACTIVO: {activo}\n"]
    for tipo in ["Ingresos", "Gastos", "Reintegros"]:
        lines.append(f"{tipo}:")
        for cat, monto in resumen[tipo].items():
            lines.append(f"  {cat}: {monto}")
        lines.append("")
    return "\n".join(lines)

# Comandos del bot
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
        append_row("Gastos", categoria.strip(), int(monto.strip()))
        await update.message.reply_text("Gasto registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /gasto Categoria: Monto")

async def reintegro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria, monto = " ".join(context.args).split(":")
        categoria = categoria.strip()
        monto = int(monto.strip())
        if categoria not in REINTEGRO_TOPES:
            await update.message.reply_text(f"Categoría inválida. Usa una de estas: {', '.join(REINTEGRO_TOPES.keys())}")
            return

        # Verificar tope mensual
        sheet = get_sheet()
        rows = sheet.get_all_records()
        total_categoria = sum(int(row["Monto"]) for row in rows if row["Tipo"] == "Reintegros" and row["Categoría"] == categoria)
        if total_categoria + monto > REINTEGRO_TOPES[categoria]:
            await update.message.reply_text(f"Tope mensual excedido para {categoria}. Máximo permitido: 400000")
            return

        append_row("Reintegros", categoria, monto)
        await update.message.reply_text("Reintegro registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /reintegro Categoria: Monto")

async def informe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resumen = generar_informe()
        await update.message.reply_text(resumen)
    except:
        await update.message.reply_text("Error al generar el informe.")

# Inicializar el bot
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
