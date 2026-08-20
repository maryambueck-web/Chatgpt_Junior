from unittest.mock import Mock, patch

from image_service import _search_image, is_image_request


def test_recognizes_common_image_requests():
    requests = [
        "Show me a picture of a red panda",
        "Can you find me some photos of space?",
        "I would like to see an image of a volcano",
        "Generate an illustration of a castle",
    ]

    assert all(is_image_request(request) for request in requests)


def test_regular_question_is_not_an_image_request():
    assert not is_image_request("What does photosynthesis mean?")


@patch("image_service.requests.get")
def test_unsplash_result_is_used_for_an_image_request(mock_get):
    response = Mock()
    response.json.return_value = {
        "results": [{"urls": {"small": "https://images.unsplash.com/photo-123"}}]
    }
    mock_get.return_value = response

    with patch.dict("image_service.os.environ", {"UNSPLASH_ACCESS_KEY": "test-key"}, clear=True):
        image_url, source = _search_image("red panda photo")

    assert image_url == "https://images.unsplash.com/photo-123"
    assert source == "unsplash"
    assert mock_get.call_args.kwargs["params"]["content_filter"] == "high"
