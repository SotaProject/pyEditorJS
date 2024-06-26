import typing as t

import bleach

from dataclasses import dataclass
from .exceptions import EditorJsParseError


__all__ = [
    "EditorJsBlock",
    "HeaderBlock",
    "ParagraphBlock",
    "ListBlock",
    "DelimiterBlock",
    "CodeBlock",
    "WarningBlock",
    "QuoteBlock",
    "MediaBlock",
    "TelegramPost",
    "RawBlock",
    "EmbedBlock"
]


def _sanitize(html: str) -> str:
    return bleach.clean(
        html,
        tags=["b", "i", "u", "a", "mark", "code", "s", "del", "br", "span"],
        attributes=["class", "data-placeholder", "href", "data-title", "data-text"],
    )


def _clean(html: str) -> str:
    return bleach.clean(
        html.replace("<br>", "\n"),
        tags=[],
        attributes=[],
    )


@dataclass
class EditorJsBlock:
    """
    A generic parsed Editor.js block
    """

    _data: dict
    """The raw JSON data of the entire block"""

    @property
    def id(self) -> t.Optional[str]:
        """
        Returns ID of the block, generated client-side.
        """

        return self._data.get("id", None)

    @property
    def type(self) -> t.Optional[str]:
        """
        Returns the type of the block.
        """

        return self._data.get("type", None)

    @property
    def data(self) -> dict:
        """
        Returns the actual block data.
        """

        return self._data.get("data", {})

    @property
    def tunes(self) -> dict:
        """
        Returns the actual block tunes.
        """

        return self._data.get("tunes", {})

    def html(self, sanitize: bool = False) -> str:
        """
        Returns the HTML representation of the block.

        ### Parameters:
        - `sanitize` - if `True`, then the block's text/contents will be sanitized.
        """

        raise NotImplementedError()


class CodeBlock(EditorJsBlock):
    @property
    def text(self) -> t.Optional[str]:
        """
        Returns the code as text.
        """
        return self.data.get("code", None)

    def html(self, sanitize: bool = False) -> str:
        return rf'<div class="cdx-block ce-code"><pre>{self.text}</pre></div>'


class HeaderBlock(EditorJsBlock):
    VALID_HEADER_LEVEL_RANGE = range(1, 7)
    """Valid range for header levels. Default is `range(1, 7)` - so, `0` - `6`."""

    @property
    def text(self) -> t.Optional[str]:
        """
        Returns the header's text.
        """

        return self.data.get("text", None)

    @property
    def level(self) -> int:
        """
        Returns the header's level (`0` - `6`).
        """

        _level = self.data.get("level", 1)

        if not isinstance(_level, int) or _level not in self.VALID_HEADER_LEVEL_RANGE:
            raise EditorJsParseError(f"`{_level}` is not a valid header level.")

        return _level

    def html(self, sanitize: bool = False) -> str:
        return rf'<h{self.level} class="cdx-block ce-header">{_sanitize(self.text) if sanitize else self.text}</h{self.level}>'


class ParagraphBlock(EditorJsBlock):
    @property
    def text(self) -> t.Optional[str]:
        """
        The text content of the paragraph.
        """

        return self.data.get("text", None)

    def html(self, sanitize: bool = False) -> str:
        classes = ['cdx-block', 'ce-paragraph']

        alignment = self.tunes.get("AlignmentTune", {"alignment": "left"})["alignment"]

        return rf'<p style="text-align: {alignment}" class="{" ".join(classes)}">{_sanitize(self.text) if sanitize else self.text}</p>'


class WarningBlock(EditorJsBlock):
    @property
    def title(self) -> t.Optional[str]:
        """
        The title content of the warning.
        """

        return self.data.get("title", None)

    @property
    def message(self) -> t.Optional[str]:
        """
        The message of the warning.
        """
        return self.data.get("message", None)

    def html(self, sanitize: bool = False) -> str:
        title = _sanitize(self.title) if sanitize else self.title
        message = _sanitize(self.message) if sanitize else self.message

        parts = [
            rf'<div class="cdx-block ce-warning">',
            f'  <blockquote class="ce-warning__blockquote">',
            f'    <b class="ce-warning__title">{title}</b>' if title else '',
            f'    <div class="ce-warning__message">{message}</div>' if message else '',
            f'  </blockquote>',
            r"</div>",
        ]

        return "".join(parts)


class QuoteBlock(EditorJsBlock):
    @property
    def text(self) -> t.Optional[str]:
        """
        The text content of the quote.
        """

        return self.data.get("text", None)

    @property
    def alignment(self) -> t.Optional[str]:
        """
        The alignment of the quote.
        """

        return self.data.get("alignment", None)

    @property
    def caption(self) -> t.Optional[str]:
        """
        The caption of the quote.
        """
        return self.data.get("caption", None)

    def html(self, sanitize: bool = False) -> str:
        caption = _sanitize(self.caption) if sanitize else self.caption
        if caption.endswith('<br>'):
            caption = caption[:-4]

        cite = (
            rf'<cite class="ce-quote__caption">{_sanitize(caption) if sanitize else caption}</cite>'
            if caption
            else ""
        )

        parts = [
            rf'<div class="cdx-block ce-quote ce-quote-with-align-{self.alignment}{" ce-quote-with-caption" if self.caption else ""}">'
            r'      <blockquote class="ce-quote__blockquote">',
            rf"{_sanitize(self.text) if sanitize else self.text}",
            f"{cite}",
            r"      </blockquote>",
            r"</div>",
        ]

        return "".join(parts)


class ListBlock(EditorJsBlock):
    VALID_STYLES = ("unordered", "ordered")
    """Valid list order styles."""

    @property
    def style(self) -> t.Optional[str]:
        """
        The style of the list. Can be `ordered` or `unordered`.
        """

        return self.data.get("style", None)

    @property
    def items(self) -> t.List[str]:
        """
        Returns the list's items, in raw format.
        """

        return self.data.get("items", [])

    def html(self, sanitize: bool = False) -> str:
        if self.style not in self.VALID_STYLES:
            raise EditorJsParseError(f"`{self.style}` is not a valid list style.")

        _items = [
            f"<li>{_sanitize(item) if sanitize else item}</li>" for item in self.items
        ]
        _type = "ul" if self.style == "unordered" else "ol"
        _items_html = "".join(_items)

        return rf'<{_type} class="cdx-block cdx-list cdx-list--{self.style}">{_items_html}</{_type}>'


class DelimiterBlock(EditorJsBlock):
    def html(self, sanitize: bool = False) -> str:
        return r'<div class="cdx-block ce-delimiter"><hr/></div>'


class RawBlock(EditorJsBlock):
    def html(self, sanitize: bool = False) -> str:
        return rf'<div class="cdx-block ce-raw">{self.data.get("html", "")}</div>'


class EmbedBlock(EditorJsBlock):

    @property
    def service(self) -> t.Optional[str]:
        """
        service of the embed.
        """

        return self.data.get("service", "")

    @property
    def source(self) -> t.Optional[str]:
        """
        source of the embed
        """

        return self.data.get("source", "")

    @property
    def embed(self) -> t.Optional[str]:
        """
        embed source of the embed
        """

        return self.data.get("embed", "")

    @property
    def caption(self) -> t.Optional[str]:
        """
        The embed's caption.
        """

        return self.data.get("caption", None)

    def html(self, sanitize: bool = False) -> str:
        caption = _sanitize(self.caption) if sanitize else self.caption
        if caption.endswith('<br>'):
            caption = caption[:-4]

        parts = [
            rf'<div class="cdx-block embed-tool embed-tool-{self.service}">'
            rf'<figure>'
            rf'<div class="embed-tool__embed">'
        ]

        if self.service == "youtube":
            parts += [
                f'<iframe src="{self.embed}" width="100%" style="aspect-ratio: 16/9" '
                f'frameborder="0" allow="accelerometer; autoplay; '
                f'clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                f'allowfullscreen></iframe>'
            ]
        elif self.service == "twitter":
            parts += [
                '<blockquote class="twitter-tweet">'
                f'<blockquote class="twitter-tweet"><a href="{self.source}"></a></blockquote>'
                f'<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
            ]
        parts += [f'</div>'
                  f'<figcaption class="embed-tool__caption">{caption}</figcaption>'
                  '</figure>'
                  '</div>']

        return "".join(parts)


class MediaBlock(EditorJsBlock):
    @property
    def file_mimetype(self) -> t.Optional[str]:
        """
        mimetype of the media file.
        """

        return self.data.get("file", {}).get("mimetype", None)

    @property
    def file_url(self) -> t.Optional[dict]:
        """
        URL of the media file.
        """

        return self.data.get("file", {}).get("urls", None)

    @property
    def caption(self) -> t.Optional[str]:
        """
        The image's caption.
        """

        return self.data.get("caption", None)

    @property
    def with_border(self) -> bool:
        """
        Whether the image has a border.
        """

        return self.data.get("withBorder", False)

    @property
    def stretched(self) -> bool:
        """
        Whether the image is stretched.
        """

        return self.data.get("stretched", False)

    @property
    def with_background(self) -> bool:
        """
        Whether the image has a background.
        """

        return self.data.get("withBackground", False)

    def html(self, sanitize: bool = False) -> str:
        _url = self.file_url

        caption = _sanitize(self.caption) if sanitize else self.caption
        if caption.endswith('<br>'):
            caption = caption[:-4]

        classes = [
            "cdx-block",
            "media-tool",
            "media-tool--filled"
        ]
        if self.stretched:
            classes.append("media-tool--stretched")
        if self.with_border:
            classes.append("media-tool--withBorder")
        if self.with_background:
            classes.append("media-tool--withBackground")

        classes_string = ' '.join(classes)

        parts = [
            rf'<div class="{classes_string}">'
            rf"<figure>"
            r'  <div class="media-tool__media">',

        ]

        if self.file_mimetype.startswith('image'):
            srcset = f'{_url.get("normal", None)} 1080w, ' \
                     f'{_url.get("medium", None)} 720w, ' \
                     f'{_url.get("small", None)} 480w' if 'image/svg' not in self.file_mimetype else []

            parts += [
                f'     <img class="media-tool__media-picture" src="{_url.get("full", "")}" ',
                f'srcset="{srcset}" ' if srcset else '',
                f'alt="{_clean(caption)}" />',
            ]
        elif self.file_mimetype.startswith('video'):
            parts += [
                rf'     <video class="media-tool__media-picture" src="{_url.get("full", "")}" controls=""></video>',
            ]

        parts += [
            r"  </div>"
            rf'<figcaption class="media-tool__caption" data-placeholder="{_clean(caption)}">{caption}</figcaption>'
            rf"</figure>"
            r"</div>",
        ]

        return "".join(parts)


class TelegramPost(EditorJsBlock):

    @property
    def messageId(self) -> t.Optional[str]:
        """
        messageId of the post.
        """

        return self.data.get("messageId", "")

    @property
    def channelName(self) -> t.Optional[str]:
        """
        channelName of the embed
        """

        return self.data.get("channelName", "")

    @property
    def embed(self) -> t.Optional[str]:
        """
        embed source of the embed
        """

        return self.data.get("embed", "")

    @property
    def caption(self) -> t.Optional[str]:
        """
        The embed's caption.
        """

        return self.data.get("caption", None)

    def html(self, sanitize: bool = False) -> str:
        parts = [
            '<div class="cdx-block telegram-post">'
            f'<script async src="https://telegram.org/js/telegram-widget.js?22" data-telegram-post="{self.channelName}/{self.messageId}" data-width="100%"></script>'
            '</div>'
        ]

        return "".join(parts)
