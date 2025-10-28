from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import cur, save
from utils import get_info_wallet



@Client.on_callback_query(filters.regex(r"^user_info$"))
async def user_info(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                 InlineKeyboardButton("💳 Histórico", callback_data="buy_history"),
                 InlineKeyboardButton("📎 FILIADOS", callback_data="filiados"),
            ],
            [
                 InlineKeyboardButton("♻️ Termos", callback_data="termos"),
                 InlineKeyboardButton("💸 Gift", callback_data="gift"),
            ],
            [
                 InlineKeyboardButton("💠 Alterar dados Pix", callback_data="swap_info"),
                 InlineKeyboardButton("🔄 Trocar CCs", callback_data="exchange"),
            ],
            [
                 InlineKeyboardButton("⚙️ Desenvolvemento Da Store", callback_data="dv"),
            ],
            [
                 InlineKeyboardButton("🔙 Voltar", callback_data="start"),
            ],
        ]
    )
    link = f"https://t.me/{c.me.username}?start={m.from_user.id}"
    await m.edit_message_text(
        f"""<b>[ ](https://d6xcmfyh68wv8.cloudfront.net/blog-content/uploads/2020/10/Card-pre-launch_blog-feature-image1.png)👤 Suas informações:</b>

<b>📛 Nome: {m.from_user.first_name}</b>
<b>🆔 ID da carteira: <code>{m.from_user.id}</code></b>

<i>♻️ - Agora Tudo Ficou Mais Facil, Use Os Botões Abaixo Para Ver Seus Históricos ou Compartilhar Seu Link De Afiliados!</i>""",
        reply_markup=kb,
    )
@Client.on_callback_query(filters.regex(r"dv$"))
async def dv(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
               InlineKeyboardButton("⚜️ Alugue Seu Bot", url="https://t.me/lzccs"),
               
            ],
            [
               InlineKeyboardButton("🔙 Voltar", callback_data="user_info"),
            ],
        ]
    )

    await m.edit_message_text(
        f"""[ ](https://i.ibb.co/t4sWF1S/Python-para-An-lise-de-Dados.webp)<b>⚙️ | Versão do bot: 5.0</b>

➤ Ultima atualização: 04/11/2023

➤ Atualizações da versão:5.0

 ➜ Opção de compra em quantidade.</b>
    
 ➜ Sistema de pontos.</b>

 ➜ Sistema de referência.</b>

 ➜ Pix com MP e Pagseguro.</b>

 ➜ Mude o Pix com 1 Click.</b>

 ➜ Sistema de ADMIN completo</b>

<b>✅ | Bot by: @lzccs</b>""",
  reply_markup=kb,
    )

@Client.on_callback_query(filters.regex(r"^buy_history$"))
async def buy_history(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🔙 Voltar", callback_data="user_info"),
            ],
        ]
    )
    history = cur.execute(
        "SELECT number, month, year, cvv FROM cards_sold WHERE owner = ? ORDER BY bought_date DESC LIMIT 50",
        [m.from_user.id],
    ).fetchall()

    if not history:
        cards_txt = "<b>Não há nenhuma compra nos registros.</b>"
    else:
        cards = []
        for card in history:
            cards.append("|".join([i for i in card]))
        cards_txt = "\n".join([f"<code>{cds}</code>" for cds in cards])

    await m.edit_message_text(
        f"""<b>💳 Histórico de compras</b>
<i>- Histórico de 50 últimas compras.</i>

{cards_txt}""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^swap$"))
async def swap_points(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🔙 Voltar", callback_data="user_info"),
            ],
        ]
    )

    user_id = m.from_user.id
    balance, diamonds = cur.execute(
        "SELECT balance, balance_diamonds FROM users WHERE id=?", [user_id]
    ).fetchone()

    if diamonds >= 50:
        add_saldo = round((diamonds / 2), 2)
        new_balance = round((balance + add_saldo), 2)

        txt = f"⚜️ Seus <b>{diamonds}</b> pontos foram convertidos em R$<b>{add_saldo}</b> de saldo."

        cur.execute(
            "UPDATE users SET balance = ?, balance_diamonds=?  WHERE id = ?",
            [new_balance, 0, user_id],
        )
        return await m.edit_message_text(txt, reply_markup=kb)

    await m.answer(
        "Você não tem pontos suficientes para realizar a troca. O mínimo é 50 pontos.",
        show_alert=True,
    )


@Client.on_callback_query(filters.regex(r"^swap_info$"))
async def swap_info(c: Client, m: CallbackQuery):
    await m.message.delete()

    cpf = await m.message.ask(
        "<b>👤 CPF da lara (válido) da lara que irá pagar</b>",
        reply_markup=ForceReply(),
        timeout=120,
    )
    name = await m.message.ask(
        "<b>👤 Nome completo do pagador</b>", reply_markup=ForceReply(), timeout=120
    )
    email = await m.message.ask(
        "<b>📧 E-mail</b>", reply_markup=ForceReply(), timeout=120
    )
    cpf, name, email = cpf.text, name.text, email.text
    cur.execute(
        "UPDATE users SET cpf = ?, name = ?, email = ?  WHERE id = ?",
        [cpf, name, email, m.from_user.id],
    )
    save()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🔙 Voltar", callback_data="start"),
            ]
        ]
    )
    await m.message.reply_text(
        "<b> Seus dados foram alterados com sucesso.</b>", reply_markup=kb
    )
