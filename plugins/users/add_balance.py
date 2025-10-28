import math
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT
from config import GRUPO_PUB
from database import cur, save
from config import BOT_LINK
from config import BOT_LINK_SUPORTE

from utils import create_mention, get_lara_info, get_support_user, insert_sold_balance


@Client.on_callback_query(filters.regex(r"^add_saldo$"))
async def add_saldo(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "💠 Pix automático", callback_data="add_saldo_auto"
                ),
                InlineKeyboardButton("🤖 Pix manual", callback_data="add_saldo_manual"),
                
            ],
            [
                InlineKeyboardButton("💰 Bitcoin", callback_data="btc"),
            ],
            [
                InlineKeyboardButton("⬅️ Voltar", callback_data="start"),
            ],
        ]
    )

    await m.edit_message_text(
        """<b>💵 Adicionar saldo</b>
<i>- Aqui abaixo vc poderá adicionar saldo de duas formas, ou <b>pix automático</b> ou <b>pix manual</b>.</i>""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^add_saldo_manual$"))
async def add_saldo_manual(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("⬅️ Voltar", callback_data="add_saldo"),
            ],
        ]
    )

    pix_name, pix_key = get_lara_info()

    support_user = get_support_user()
    valor_min = 20
    details = (
        f"\n\n<i>⚠️ Não envie um valor</i> <b>Menor</b> <i>que R$ {valor_min}, pois se você enviar perderá seu dinheiro.</i>"
        if valor_min
        else ""
    )
    await m.edit_message_text(
        f"""<b>🤖 Pix manual</b>
Para adicionar saldo manualmente, copie a chave PIX abaixo e faça o pagamento, após feito mande o comprovante para o dono do BOT, assim seu saldo será adicionado por ele.

<b>🏦 DADOS DA CONTA 🏦</b>

<b>Nome:</b> <code>{pix_name}</code>
<b>Chave Pix:</b> <code>{pix_key}</code>

<b>⚠️ Se vc já fez o pagamento, envie o comprovante para {BOT_LINK_SUPORTE}
{details}""",
        reply_markup=kb,
    )

@Client.on_callback_query(filters.regex(r"^btc$"))
async def btc(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("⚠️", callback_data="add_saldo"),
            ],
        ]
    )

    pix_name, pix_key = get_lara_info()

    support_user = BOT_LINK_SUPORTE
    valor_min = 20
    details = (
        f"\n\n<i>⚠️ Não envie um valor</i> <b>Menor</b> <i>que R$ {valor_min}, pois se você enviar perderá seu dinheiro.</i>"
        if valor_min
        else ""
    )
    await m.edit_message_text(
        f"""<b>💰Bitcoin Manual</b>\n\n
Para adicionar saldo via Bitcoin, envie a quantia que desejar para nosso endereço Bitcoin, segue o endereço:\n\n

<code>Endereço aqui</code>\n\n

Após enviar, chame {support_user} e mande o link da transação.
Será adicionado exatamente o valor que chegar à carteira.
{details}""",
        reply_markup=kb,
    )        


@Client.on_message(filters.regex(r"/resgatar (?P<gift>\w+)$"))
@Client.on_callback_query(filters.regex(r"^resgatar (?P<gift>\w+)$"))
async def resgatar_gift(c: Client, m: Union[CallbackQuery, Message]):
    user_id = m.from_user.id
    gift = m.matches[0]["gift"]

    if isinstance(m, Message):
        send = m.reply_text
    else:
        send = m.edit_message_text

    try:
        value = cur.execute(
            "SELECT value from gifts WHERE token = ?", [gift]
        ).fetchone()[0]
    except:
        return await send("<b>⚠️ Gift card não existente ou já resgatado, digite /pix para realizar uma tranferencia.</b>")

    cur.execute("DELETE FROM gifts WHERE token = ?", [gift])

    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", [value, user_id]
    ).fetchone()

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    mention = create_mention(m.from_user)
    insert_sold_balance(value, user_id, "manual")
    base = f"""gifit resgatado pelo {mention}"""

    await c.send_message(ADMIN_CHAT, base)
    
    kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Acessar loja",url="https://t.me/MurderStore_Bot"
                            ),
                        ],
                    ]
                )
    mention = m.from_user.first_name
    base = f"""<a href='https://t.me/hypersuporte'>&#8204</a>🎁 {mention} resgatou um gift card de <b>R${value}</b>
<b>Obrigado {mention} pela a preferência</b>
- Gift card: <code>{gift[0:6]}</code>\n<a href='https://t.me/MurderSupport24h'>Suporte</a>"""
    await c.send_message(GRUPO_PUB, base, reply_markup=kb)

    if isinstance(m, CallbackQuery):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        "🛒 Voltar ao bot",
                        url=f"https://t.me/{c.me.username}?start=start",
                    ),
                ],
            ]
        )
        await send(
            f"<b>🎁 {m.from_user.first_name} resgatou R$ {value} no bot via gift card.</b>",
            reply_markup=kb,
        )
    else:
        await send(
            f"<b>🎉 Agora sim 👏 foi adicionado R$ {value} em sua conta no bot.</b>"
        )

    """
    refer = cur.execute("SELECT refer FROM users WHERE id = ?", [user_id]).fetchone()[0]

    if refer:
        quantity = math.floor((value / 100) * 5)  # 5% normalizado para int.
        if quantity > 0:
            mention = create_mention(m.from_user, with_id=False)

            cur.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                [quantity, refer],
            ).fetchone()

            await c.send_message(
                int(refer),
                f"💸 Seu referenciado {mention} adicionou saldo no bot e você recebeu {quantity} de saldo.",
            )
    """
    save()
