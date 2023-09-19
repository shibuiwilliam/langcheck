from __future__ import annotations

import abc
from collections.abc import Iterator

from janome.tokenizer import Tokenizer
from rouge_score.tokenizers import Tokenizer as BaseTokenizer

# Japanese punctuation characters
_PUNCTUATIONS = ['、', '。', '，', '．', ',', '.', "?", "!", "？", "！"]


class _JapaneseTokenizer(BaseTokenizer):

    @abc.abstractmethod
    def _tokenize(self, text: str) -> Iterator[str]:
        raise NotImplementedError(
            "Tokenizer for Japanese must override `_tokenize()` method")

    def tokenize(self, text: str) -> list[str]:
        tokens = self._tokenize(text)
        return [
            token for token in tokens if (token and token not in _PUNCTUATIONS)
        ]


class MeCabTokenizer(_JapaneseTokenizer):
    '''
    An optional tokenizer for caliculating rouge score base on MeCab.

    .. note::
        The advantage of using MeCab is that the core implementation is written
        in a compiled language and runs much faster than Janome. If you are
        processing large data, consider setting up MeCab and using the
        MeCabTokenizer.
        On the other hand, it takes more effort to install it on some
        environments and may not work. Please refer to the official page if the
        Python wrapper, mecab-python3, does not work in your environment.
    '''

    class _MeCabNodeSurfaceIterator(Iterator):

        def __init__(self, node) -> None:
            self._node = node

        def __next__(self):
            if self._node is None:
                raise StopIteration
            else:
                node = self._node
                self._node = self._node.next
                return node.surface

    def __init__(self):
        import MeCab
        self.tokenizer = MeCab.Tagger()

    def _tokenize(self, text):
        return MeCabTokenizer._MeCabNodeSurfaceIterator(
            self.tokenizer.parseToNode(text))


class JanomeTokenizer(_JapaneseTokenizer):
    '''Janome based Tokenizer for Japanese.

    The default tokenizer for caliculating rouge score base on Janome.

    .. note::
        The advantage of using Janome is that it is a pure Python library and
        introduces no additional dependencies.
        On the other hand, it takes more time to parse sentences than a MeCab
        -based tokenizer. Specifically, it takes seconds every time when
        constructing this class since the Janome tokenizer loads the entire
        dictionary during initialization.
        If you are processing large data, consider setting up MeCab and using
        the MeCabTokenizer.
    '''

    def __init__(self):
        self.tokenizer = Tokenizer()

    def _tokenize(self, text: str):
        return self.tokenizer.tokenize(text, wakati=True)
