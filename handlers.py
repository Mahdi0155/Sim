# ───────────────────── Handlers ─────────────────────

async def ensure_user(update: Update):
    if not update.effective_user:
        return
    u = update.effective_user
    async with DBSession() as s:
        await s.merge(User(id=u.id, username=u.username, first_name=u.first_name, last_name=u.last_name))
        await s.commit()

async def on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update)

    args = ctx.args
    if args and args[0].startswith(DL_PREFIX):
        code = args[0][len(DL_PREFIX):]
        await send_batch_with_membership(update, ctx, code)
        return

    if await is_admin(update.effective_user.id):  # type: ignore
        await update.message.reply_text("به پنل ادمین خوش آمدید", reply_markup=ADMIN_PANEL_KB)
    else:
        await update.message.reply_text("سلام! لینک اختصاصی دریافت فایل را ارسال/لمس کنید.")

async def on_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):  # type: ignore
        return
    await update.message.reply_text("پنل ادمین", reply_markup=ADMIN_PANEL_KB)

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update)
    text = update.message.text
    uid = update.effective_user.id  # type: ignore

    if text == "↩️ بازگشت به پنل":
        await update.message.reply_text("بازگشت", reply_markup=ADMIN_PANEL_KB)
        UPLOAD_STATE.pop(uid, None)
        return

    if not await is_admin(uid):
        return

    if text == "آپلود📂":
        UPLOAD_STATE[uid] = {"items": []}
        await update.message.reply_text(
            f"تا {MAX_UPLOAD} فایل/رسانه/کپشن ارسال کنید. در پایان روی 'مرحله بعد↩️' بزنید.",
            reply_markup=ReplyKeyboardMarkup([["مرحله بعد↩️"], ["↩️ بازگشت به پنل"]], resize_keyboard=True)
        )
        return

    if text == "مرحله بعد↩️":
        st = UPLOAD_STATE.get(uid)
        if not st or not st["items"]:
            await update.message.reply_text("چیزی ارسال نشده.")
            return
        async with DBSession() as s:
            batch = FileBatch.make()
            s.add(batch)
            await s.flush()
            for it in st["items"]:
                s.add(FileItem.from_state(batch.id, **it))
            await s.commit()
            code = batch.code

        # Post to channel now and store channel message ids
        async with DBSession() as s:
            batch = await s.get(FileBatch, code)
            posted_ids: List[int] = []
            for item in (await s.execute(FileItem.select_by_batch(code))).scalars().all():
                try:
                    if item.kind == "photo":
                        msg = await ctx.bot.send_photo(CHANNEL_UPLOAD_ID, item.file_id, caption=item.caption or None)
                    elif item.kind == "video":
                        msg = await ctx.bot.send_video(CHANNEL_UPLOAD_ID, item.file_id, caption=item.caption or None)
                    elif item.kind == "audio":
                        msg = await ctx.bot.send_audio(CHANNEL_UPLOAD_ID, item.file_id, caption=item.caption or None)
                    else:
                        msg = await ctx.bot.send_document(CHANNEL_UPLOAD_ID, item.file_id, caption=item.caption or None)
                    posted_ids.append(msg.message_id)
                except Exception as e:
                    logger.error(f"post to channel failed: {e}")
            batch.channel_message_ids = posted_ids
            await s.commit()

        me = await ctx.bot.get_me()
        link = make_deeplink(code, me.username)
        await update.message.reply_text(
            f"لینک اختصاصی آماده شد:\n{link}\n\nآن را در کانال خود قرار دهید.",
            reply_markup=ADMIN_PANEL_KB
        )
        UPLOAD_STATE.pop(uid, None)
        return

    if text == "ارسال همگانی📩":
        ctx.chat_data["broadcast"] = {"pending": True}
        await update.message.reply_text("پیام همگانی را بفرستید.", reply_markup=BACK_TO_PANEL_KB)
        return

    if text == "تنظیم کانال🔒":
        await update.message.reply_text(
            "برای افزودن کانال، یکی از این کارها را انجام دهید:\n1) لینک دعوت مانند https://t.me/+xxxx را بفرستید\n2) یک پیام از همان کانال فوروارد کنید\n— برای حذف، همین لینک را دوباره بفرستید.",
            reply_markup=BACK_TO_PANEL_KB
        )
        ctx.chat_data["channel_cfg"] = True
        return

    if text == "آمار📊":
        async with DBSession() as s:
            users_total = await s.count_users()
            users_1h = await s.count_users_since(timedelta(hours=1))
            users_24h = await s.count_users_since(timedelta(hours=24))
            users_7d = await s.count_users_since(timedelta(days=7))
            users_30d = await s.count_users_since(timedelta(days=30))
            files_total = await s.count_files()
        t, d = fmt_now_tz()
        await update.message.reply_text(
            f"🤖 امار شما در ساعت {t} و تاریخ {d} به این صورت میباشد\n\n"
            f"👥 تعداد اعضا : {users_total:,}\n"
            f"🕒 تعداد کاربران ساعت گذشته : {users_1h:,}\n"
            f"☪️ تعداد کاربران 24 ساعت گذشته : {users_24h:,}\n"
            f"7️⃣ تعداد کاربران هفته گذشته : {users_7d:,}\n"
            f"🌛 تعداد کاربران ماه گذشته : {users_30d:,}\n"
            f"🗂 تعداد فایل ها : {files_total:,}",
            reply_markup=ADMIN_PANEL_KB
        )
        return

    if text == "تنظیمات بیشتر":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("افزودن ادمین", callback_data="cfg:add_admin")],
            [InlineKeyboardButton("حذف ادمین", callback_data="cfg:del_admin")],
            [InlineKeyboardButton("تنظیم زمان حذف فایل", callback_data="cfg:ttl")],
            [InlineKeyboardButton("گزارش لینک اختصاصی", callback_data="cfg:link_stat")],
        ])
        await update.message.reply_text("تنظیمات:", reply_markup=kb)
        return

    # Add/remove channel or broadcast capture
    if ctx.chat_data.get("channel_cfg"):
        await add_or_remove_channel(update, ctx, text)
        return

    if ctx.chat_data.get("broadcast", {}).get("pending"):
        ctx.chat_data["broadcast"]["text"] = text
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("تایید ✅", callback_data="bcf:yes"), InlineKeyboardButton("لغو ❌", callback_data="bcf:no")]
        ])
        await update.message.reply_text("ارسال برای همه تایید می‌شود؟", reply_markup=kb)
        return

async def on_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id  # type: ignore
    st = UPLOAD_STATE.get(uid)
    if not st:
        return
    if len(st["items"]) >= MAX_UPLOAD:
        await update.message.reply_text("به حد مجاز رسید.")
        return

    kind = None
    file_id = None
    caption = update.message.caption

    if update.message.photo:
        kind = "photo"
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        kind = "video"
        file_id = update.message.video.file_id
    elif update.message.audio:
        kind = "audio"
        file_id = update.message.audio.file_id
    elif update.message.document:
        kind = "document"
        file_id = update.message.document.file_id
    else:
        return

    st["items"].append({"kind": kind, "file_id": file_id, "caption": caption})
    await update.message.reply_text(f"افزوده شد ({len(st['items'])}/{MAX_UPLOAD}).")

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id

    # Broadcast confirm
    if data in ("bcf:yes", "bcf:no"):
        await q.answer()
        pend = ctx.chat_data.get("broadcast", {}).get("pending")
        if not pend:
            return
        if data == "bcf:no":
            ctx.chat_data["broadcast"] = {}
            await q.edit_message_text("لغو شد.")
            return
        text = ctx.chat_data["broadcast"].get("text")
        await q.edit_message_text("در حال ارسال...")
        sent = 0
        async with DBSession() as s:
            users = (await s.execute(User.select_all_ids())).scalars().all()
        for uid2 in users:
            try:
                await ctx.bot.send_message(uid2, text)
                sent += 1
            except Exception:
                pass
        ctx.chat_data["broadcast"] = {}
        await ctx.bot.send_message(uid, f"تمام شد. ارسال شد: {sent}")
        return

    # Settings flow
    if data.startswith("cfg:"):
        _, action = data.split(":", 1)
        if action == "add_admin":
            ctx.user_data["cfg_mode"] = "add_admin"
            await q.edit_message_text("آیدی عددی کاربر را بفرستید.")
        elif action == "del_admin":
            ctx.user_data["cfg_mode"] = "del_admin"
            await q.edit_message_text("آیدی عددی کاربر را بفرستید (فقط ادمین اصلی).")
        elif action == "ttl":
            ctx.user_data["cfg_mode"] = "ttl"
            await q.edit_message_text("زمان حذف فایل (ثانیه) را بفرستید.")
        elif action == "link_stat":
            ctx.user_data["cfg_mode"] = "link_stat"
            await q.edit_message_text("کد لینک یا خود لینک دیپ-لینک را بفرستید.")
        return

    # Membership confirmation button: data like conf:<code>
    if data.startswith("conf:"):
        _, code = data.split(":", 1)
        await q.answer()
        await q.message.delete()
        await send_batch_with_membership(update, ctx, code)
        return

# Text input for settings modes
@telegram_app.message_handler if False: ...  # placeholder to remind structure

async def add_or_remove_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str):
    async with DBSession() as s:
        # If link exists -> toggle remove; else add
        link = text.strip()
        chat_id = None
        title = None
        # If message is a forwarded channel message, extract chat id/title
        if update.message.forward_from_chat:
            chat_id = update.message.forward_from_chat.id
            title = update.message.forward_from_chat.title
        # Try resolving from link (best-effort)
        if chat_id is None and link.startswith("http"):
            try:
                chat = await ctx.bot.get_chat(link)
                chat_id = chat.id
                title = chat.title or chat.username
            except Exception:
                pass
        # Toggle remove if exists
        existing = (await s.execute(ForcedChannel.select_by_link(link))).scalar_one_or_none()
        if existing:
            await s.delete(existing)
            await s.commit()
            await update.message.reply_text("کانال حذف شد.")
            return
        # Otherwise add
        fc = ForcedChannel(link=link, chat_id=chat_id, title=title)
        s.add(fc)
        await s.commit()
        await update.message.reply_text("افزوده شد.")

async def send_membership_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str, not_joined: List[ForcedChannel]):
    buttons = []
    for ch in not_joined:
        name = ch.title or ch.link
        buttons.append([InlineKeyboardButton(name, url=ch.link)])
    buttons.append([InlineKeyboardButton("تایید عضویت", callback_data=f"conf:{code}")])
    kb = InlineKeyboardMarkup(buttons)
    await update.effective_message.reply_text(
        "برای دریافت فایل‌ها، ابتدا در کانال‌های زیر عضو شوید.", reply_markup=kb
    )

async def send_and_schedule_delete(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: List[int], ttl: int):
    try:
        for mid in message_ids:
            await ctx.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_UPLOAD_ID, message_id=mid)
        warn = await ctx.bot.send_message(chat_id, f"⚠️ این پیام‌ها پس از {ttl} ثانیه حذف می‌شوند.")
        await asyncio.sleep(ttl)
        # delete recent messages from this chat (best-effort)
        # Note: We don't have message ids of copied messages, so we delete the warning only.
        await ctx.bot.delete_message(chat_id, warn.message_id)
    except Exception as e:
        logger.warning(f"schedule delete failed: {e}")

async def send_batch_with_membership(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str):
    user_id = update.effective_user.id  # type: ignore
    not_joined = await check_forced_membership(ctx, user_id)
    if not_joined:
        # Show only channels not yet verified as joined
        await send_membership_prompt(update, ctx, code, not_joined)
        return

    # All good, deliver
    async with DBSession() as s:
        batch = await s.get(FileBatch, code)
        if not batch:
            await update.effective_message.reply_text("لینک نامعتبر است.")
            return
        ttl = (await Setting.get_delete_after(s)) or DELETE_AFTER_SECONDS_DEFAULT
        # track hit
        s.add(LinkHit(code=code, user_id=user_id))
        await s.commit()
        await send_and_schedule_delete(ctx, update.effective_chat.id, batch.channel_message_ids or [], ttl)

# Process free-form numbers for settings modes
async def process_config_modes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("cfg_mode")
    if not mode:
        return False
    text = update.message.text.strip()
    async with DBSession() as s:
        if mode == "add_admin":
            try:
                uid = int(text)
                s.add(AdminUser(id=uid))
                await s.commit()
                await update.message.reply_text("افزوده شد.")
            except Exception:
                await update.message.reply_text("نامعتبر.")
        elif mode == "del_admin":
            if not await ensure_owner(update.effective_user.id):  # type: ignore
                await update.message.reply_text("فقط ادمین اصلی.")
            else:
                try:
                    uid = int(text)
                    au = await s.get(AdminUser, uid)
                    if au:
                        await s.delete(au)
                        await s.commit()
                        await update.message.reply_text("حذف شد.")
                    else:
                        await update.message.reply_text("یافت نشد.")
                except Exception:
                    await update.message.reply_text("نامعتبر.")
        elif mode == "ttl":
            try:
                v = max(10, int(text))
                await Setting.set_delete_after(s, v)
                await s.commit()
                await update.message.reply_text("ذخیره شد.")
            except Exception:
                await update.message.reply_text("نامعتبر.")
        elif mode == "link_stat":
            code = text
            if code.startswith("http") and "?start=" in code:
                code = code.split("?start=")[-1]
                if code.startswith(DL_PREFIX):
                    code = code[len(DL_PREFIX):]
            hits = (await s.execute(LinkHit.count_by_code(code))).scalar_one_or_none() or 0
            await update.message.reply_text(f"تعداد دریافت: {hits}")
    ctx.user_data["cfg_mode"] = None
    return True

# Hook into on_text for config modes
orig_on_text = on_text
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await process_config_modes(update, ctx):
        return
    await orig_on_text(update, ctx)
