from PIL import Image, ImageDraw


def fit_text(draw, text, font, max_width):
    text = str(text or "")
    if max_width <= 0:
        return ""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text

    ellipsis = "..."
    ellipsis_bbox = draw.textbbox((0, 0), ellipsis, font=font)
    if ellipsis_bbox[2] - ellipsis_bbox[0] > max_width:
        return ""

    for end in range(len(text), 0, -1):
        candidate = text[:end].rstrip() + ellipsis
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return candidate
    return ellipsis


def _draw_centered_text(
    draw,
    x,
    y,
    width,
    text,
    font,
    fill,
    stroke_width=0,
    stroke_fill=None,
):
    if not text:
        return
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_x = x + max(0, (width - text_w) // 2)
    kwargs = {"font": font, "fill": fill}
    if stroke_width:
        kwargs["stroke_width"] = stroke_width
        kwargs["stroke_fill"] = stroke_fill or (0, 0, 0)
    draw.text((text_x, y), text, **kwargs)


def draw_rounded_avatar(base, avatar, xy, size, radius):
    avatar = avatar.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size, size),
        radius=radius,
        fill=255,
    )
    base.paste(avatar, xy, mask)


def draw_member_profile(
    base,
    draw,
    member_profile,
    member_avatar,
    box,
    font_name,
    font_small,
    *,
    avatar_size=44,
    avatar_radius=12,
    nick_fill=(255, 255, 255, 235),
    qq_fill=(180, 210, 235, 180),
    placeholder_fill=(70, 90, 120, 220),
    stroke_width=0,
    stroke_fill=None,
):
    if not member_profile:
        return

    x, y, w, h = box
    avatar_x = x + max(0, (w - avatar_size) // 2)
    avatar_y = y
    if member_avatar:
        draw_rounded_avatar(base, member_avatar, (avatar_x, avatar_y), avatar_size, avatar_radius)
    else:
        draw.rounded_rectangle(
            (avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size),
            radius=avatar_radius,
            fill=placeholder_fill,
        )
        initial = str(member_profile.get("name") or member_profile.get("qq") or "?")[:1]
        _draw_centered_text(
            draw,
            avatar_x,
            avatar_y + max(0, avatar_size // 2 - 10),
            avatar_size,
            initial,
            font_name,
            nick_fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )

    nick = fit_text(draw, member_profile.get("name") or member_profile.get("qq"), font_name, w)
    qq = str(member_profile.get("qq") or "")
    qq_text = fit_text(draw, f"QQ {qq}" if qq else "", font_small, w)

    nick_y = avatar_y + avatar_size + 6
    _draw_centered_text(
        draw,
        x,
        nick_y,
        w,
        nick,
        font_name,
        nick_fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    if nick_y + 18 < y + h:
        _draw_centered_text(
            draw,
            x,
            nick_y + 18,
            w,
            qq_text,
            font_small,
            qq_fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
