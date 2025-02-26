from __future__ import annotations

from typing import Dict, List, Optional

import torch
from rouge_score import rouge_scorer
from rouge_score.tokenizers import Tokenizer
from sentence_transformers import SentenceTransformer, util

from langcheck.metrics._validation import validate_parameters_reference_based
from langcheck.metrics.en.reference_based_text_quality import \
    semantic_similarity as en_semantic_similarity
from langcheck.metrics.ja._tokenizers import JanomeTokenizer
from langcheck.metrics.metric_value import MetricValue


def semantic_similarity(
        generated_outputs: List[str] | str,
        reference_outputs: List[str] | str,
        prompts: Optional[List[str] | str] = None,
        embedding_model_type: str = 'local',
        openai_args: Optional[Dict[str, str]] = None) -> MetricValue[float]:
    '''Calculates the semantic similarities between the generated outputs and
    the reference outputs. The similarities are computed as the cosine
    similarities between the generated and reference embeddings. This metric
    takes on float values between [-1, 1], but typically ranges between 0 and 1
    where 0 is minimum similarity and 1 is maximum similarity. (NOTE: when using
    OpenAI embeddings, the cosine similarities tend to be skewed quite heavily
    towards higher numbers.)

    We currently support two embedding model types:

    1. The 'local' type, where the 'paraphrase-multilingual-mpnet-base-v2' model
    is downloaded from HuggingFace and run locally. This is the default model
    type and there is no setup needed to run this.

    2. The 'openai' type, where we use OpenAI's 'text-embedding-ada-002' model
    by default (this is configurable). See
    https://langcheck.readthedocs.io/en/latest/metrics.html#computing-metrics-with-openai-models  # NOQA E501
    for examples on setting up the OpenAI API key.

    Ref:
        https://huggingface.co/tasks/sentence-similarity
        https://www.sbert.net/docs/usage/semantic_textual_similarity.html
        https://openai.com/blog/new-and-improved-embedding-model

    Args:
        generated_outputs: The model generated output(s) to evaluate
        reference_outputs: The reference output(s)
        prompts: The prompts used to generate the output(s). Prompts are
            optional metadata and not used to calculate the metric.
        embedding_model_type: The type of embedding model to use ('local' or
            'openai'), default 'local'
        openai_args: Dict of additional args to pass in to the
            `openai.Embedding.create` function, default None

    Returns:
        An :class:`~langcheck.metrics.metric_value.MetricValue` object
    '''
    generated_outputs, reference_outputs, prompts = validate_parameters_reference_based(  # NOQA E501
        generated_outputs, reference_outputs, prompts)
    assert embedding_model_type in [
        'local', 'openai'
    ], ('Unsupported embedding model type. '
        'The supported ones are ["local", "openai"]')

    if embedding_model_type == 'openai':
        # We can use the same API as english semantic_similarity to compare the
        # similarity
        metric_value = en_semantic_similarity(generated_outputs,
                                              reference_outputs, prompts,
                                              embedding_model_type, openai_args)
        metric_value.language = 'ja'
        return metric_value

    # According to the blog post,
    # 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2' has the best
    # performance on Japanese dataset.
    # Ref:
    # https://tech.yellowback.net/posts/sentence-transformers-japanese-models
    model = SentenceTransformer(
        'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    generated_embeddings = model.encode(generated_outputs)
    reference_embeddings = model.encode(reference_outputs)
    cosine_scores = util.pairwise_cos_sim(generated_embeddings,
                                          reference_embeddings)
    # Numerical instability can cause the dot product of almost identical
    # vectors to exceed 1.0 slightly, so we clip the outputs
    cosine_scores = torch.clamp(cosine_scores, -1.0, 1.0)

    return MetricValue(metric_name='semantic_similarity',
                       prompts=prompts,
                       generated_outputs=generated_outputs,
                       reference_outputs=reference_outputs,
                       sources=None,
                       metric_values=cosine_scores.tolist(),
                       language='ja')


def rouge1(generated_outputs: List[str] | str,
           reference_outputs: List[str] | str,
           prompts: Optional[List[str] | str] = None,
           *,
           tokenizer: Optional[Tokenizer] = None) -> MetricValue[float]:
    '''Calculates the F1 metrics of the ROUGE-1 scores between the generated
    (single tokens) between the generated outputs and the reference outputs.
    This metric takes on float values between [0, 1], where 0 is no overlap and
    1 is complete overlap.

    Ref:
        https://github.com/google-research/google-research/tree/master/rouge

    Args:
        generated_outputs: The model generated output(s) to evaluate
        reference_outputs: The reference output(s)
        prompts: The prompts used to generate the output(s). Prompts are
            optional metadata and not used to calculate the metric.

    Returns:
        An MetricValue object
    '''
    generated_outputs, reference_outputs, prompts = validate_parameters_reference_based(  # NOQA E501
        generated_outputs, reference_outputs, prompts)

    scores = _rouge(generated_outputs,
                    reference_outputs,
                    'rouge1',
                    tokenizer=tokenizer)
    return MetricValue(metric_name='rouge1',
                       prompts=prompts,
                       generated_outputs=generated_outputs,
                       reference_outputs=reference_outputs,
                       sources=None,
                       metric_values=scores,
                       language='ja')


def rouge2(generated_outputs: List[str] | str,
           reference_outputs: List[str] | str,
           prompts: Optional[List[str] | str] = None,
           *,
           tokenizer: Optional[Tokenizer] = None) -> MetricValue[float]:
    '''Calculates the F1 metrics of the ROUGE-2 scores between the generated
    outputs and the reference outputs. It evaluates the overlap of bigrams
    (two adjacent tokens) between the generated outputs and the reference
    outputs. This metric takes on float values between [0, 1], where 0 is no
    overlap and 1 is complete overlap.

    Ref:
        https://github.com/google-research/google-research/tree/master/rouge

    Args:
        generated_outputs: The model generated output(s) to evaluate
        reference_outputs: The reference output(s)
        prompts: The prompts used to generate the output(s). Prompts are
            optional metadata and not used to calculate the metric.

    Returns:
        An MetricValue object
    '''
    generated_outputs, reference_outputs, prompts = validate_parameters_reference_based(  # NOQA E501
        generated_outputs, reference_outputs, prompts)

    scores = _rouge(generated_outputs,
                    reference_outputs,
                    'rouge2',
                    tokenizer=tokenizer)
    return MetricValue(metric_name='rouge2',
                       prompts=prompts,
                       generated_outputs=generated_outputs,
                       reference_outputs=reference_outputs,
                       sources=None,
                       metric_values=scores,
                       language='ja')


def rougeL(generated_outputs: List[str] | str,
           reference_outputs: List[str] | str,
           prompts: Optional[List[str] | str] = None,
           *,
           tokenizer: Optional[Tokenizer] = None) -> MetricValue[float]:
    '''Calculates the F1 metrics of the ROUGE-L scores between the generated
    outputs and the reference outputs. It evaluates the longest common
    subsequence (LCS) between the generated outputs and the reference outputs.
    This metric takes on float values between [0, 1], where 0 means that the LCS
    is empty and 1 means that the reference and generated outputs are the same.

    Ref:
        https://github.com/google-research/google-research/tree/master/rouge

    Args:
        generated_outputs: The model generated output(s) to evaluate
        reference_outputs: The reference output(s)
        prompts: The prompts used to generate the output(s). Prompts are
            optional metadata and not used to calculate the metric.

    Returns:
        An MetricValue object
    '''
    generated_outputs, reference_outputs, prompts = validate_parameters_reference_based(  # NOQA E501
        generated_outputs, reference_outputs, prompts)

    # The `rouge_score` package has two flavors of ROUGE-L [1]:
    # - 1) sentence-level, where newline characters are ignored
    # - 2) summary-level, where newline characters are interpreted as sentence
    #      boundaries
    #
    # We use (2) here (i.e. `rougeLsum`) because this is how `pyrouge` computes
    # the ROUGE-L score (https://github.com/bheinzerling/pyrouge), which is a
    # Python wrapper around original perl script implementation.
    #
    # [1] https://github.com/google-research/google-research/tree/master/rouge#two-flavors-of-rouge-l # NOQA E501
    scores = _rouge(generated_outputs,
                    reference_outputs,
                    'rougeLsum',
                    tokenizer=tokenizer)
    return MetricValue(metric_name='rougeL',
                       prompts=prompts,
                       generated_outputs=generated_outputs,
                       reference_outputs=reference_outputs,
                       sources=None,
                       metric_values=scores,
                       language='ja')


def _rouge(generated_outputs: List[str],
           reference_outputs: List[str],
           rouge_type: str,
           *,
           tokenizer: Optional[Tokenizer] = None) -> List[float]:
    '''Helper function for computing the rouge1, rouge2, and rougeL metrics.
    This uses Google Research's implementation of ROUGE:
    https://github.com/google-research/google-research/tree/master/rouge

    Args:
        generated_outputs: A list of model generated outputs to evaluate
        reference_outputs: A list of reference outputs
        rouge_type: rouge1, rouge2, or rougeLsum

    Returns:
        A list of F1 values of the ROUGE scores
    '''
    assert rouge_type in ['rouge1', 'rouge2', 'rougeLsum']

    # The tokenizer is default to JanomeTokenizer
    tokenizer = tokenizer or JanomeTokenizer()
    scorer = rouge_scorer.RougeScorer([rouge_type],
                                      use_stemmer=True,
                                      tokenizer=tokenizer)
    scores = []
    for gen, ref in zip(generated_outputs, reference_outputs):
        score = scorer.score(gen, ref)
        scores.append(score[rouge_type].fmeasure)
    return scores
