from unittest.mock import Mock, patch

import pytest

from langcheck.eval.ja import sentiment, tateishi_ono_yamada_reading_ease
from tests.utils import is_close

################################################################################
# Tests
################################################################################


@pytest.mark.parametrize('generated_outputs', [
    'こんにちは',
    ['こんにちは'],
    ["私は嬉しい", "私は悲しい"],
])
def test_sentiment(generated_outputs):
    eval_value = sentiment(generated_outputs)
    assert all(0 <= v <= 1 for v in eval_value.metric_values)


@pytest.mark.parametrize('generated_outputs', ["私は嬉しい", ["私は嬉しい"]])
def test_sentiment_openai(generated_outputs):
    mock_chat_response = {
        'choices': [{
            'message': {
                'function_call': {
                    'arguments': "{\n  \"sentiment\": \"Positive\"\n}"
                }
            }
        }]
    }
    # Calling the openai.ChatCompletion.create method requires an OpenAI API
    # key, so we mock the return value instead
    with patch('openai.ChatCompletion.create',
               Mock(return_value=mock_chat_response)):
        eval_value = sentiment(generated_outputs, model_type='openai')
        # "Positive" gets a value of 1.0
        assert eval_value.metric_values[0] == 1


@pytest.mark.parametrize('generated_outputs,metric_values', [
    ('吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。',
     [73.499359]),
    (['吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。'
     ], [73.499359]),
    (['日本語自然言語処理には、日本語独特の技法が多数必要で、欧米系言語と比較して難易度が高い。'], [24.7875]),
])
def test_tateishi_ono_yamada_reading_ease(generated_outputs, metric_values):
    eval_value = tateishi_ono_yamada_reading_ease(generated_outputs)
    assert is_close(eval_value.metric_values, metric_values)
