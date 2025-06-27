import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DATA_FILE = "data.json"
REINTEGRO_TOPES = {
    "Supermercado": 400000,
    "Combustible": 400000,
    "Tienda": 400000,
    "Bares": 400000,
    "Pagopar": 400000,
    "Biggie": 400000
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"ACTIVO": 0, "Ingresos": {}, "Gastos": {}, "Reintegros": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_data(category, subcategory, amount):
    data = load_data()
    if subcategory not in data[category]:
        data[category][subcategory] = 0
    data[category][subcategory] += amount
    if category == "Ingresos":
        data["ACTIVO"] += amount
    elif category == "Gastos":
        data["ACTIVO"] -= amount
    save_data(data)

def update_reintegro(categoria, amount):
    data = load_data()
    if categoria not in REINTEGRO_TOPES:
        return False, f"Categoría inválida. Usa una de estas: {', '.join(REINTEGRO_TOPES.keys())}"
    if categoria not in data["Reintegros"]:
        data["Reintegros"][categoria] = 0
    if data["Reintegros"][categoria] + amount > REINTEGRO_TOPES[categoria]:
        return False, f"Tope mensual excedido para {categoria}. Máximo permitido: 400000"
    data["Reintegros"][categoria] += amount
    data["ACTIVO"] += amount
    save_data(data)
    return True, "Reintegro registrado."

async def ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subcat, amount = " ".join(context.args).split(":")
        update_data("Ingresos", subcat.strip(), int(amount.strip()))
        await update.message.reply_text("Ingreso registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /ingreso Subcategoria: Monto")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subcat, amount = " ".join(context.args).split(":")
        update_data("Gastos", subcat.strip(), int(amount.strip()))
        await update.message.reply_text("Gasto registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /gasto Subcategoria: Monto")

async def reintegro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria, amount = " ".join(context.args).split(":")
        success, message = update_reintegro(categoria.strip(), int(amount.strip()))
        await update.message.reply_text(message)
    except:
        await update.message.reply_text("Formato incorrecto. Usa /reintegro Categoria: Monto")

async def informe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lines = [f"ACTIVO: {data['ACTIVO']}\n"]
    for cat in ["Ingresos", "Gastos"]:
        lines.append(f"{cat}:")
        for subcat, amount in data[cat].items():
            lines.append(f"  {subcat}: {amount}")
        lines.append("")
    lines.append("Reintegros:")
    for categoria, amount in data["Reintegros"].items():
        lines.append(f"  {categoria}: {amount}")
    await update.message.reply_text("\n".join(lines))

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
