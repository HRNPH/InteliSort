import modal
from dotenv import load_dotenv
load_dotenv()

def call_sentence_encoder(sentences: list[str]) -> list[list[float]]:
    """
    Calls the sentence-encoder function in the modal package.
    params: sentences: list[str] - a list of sentences to encode
    returns: list[list[float]] - a list of lists of floats, representing the embeddings of the sentences
    """
    try:
        inf_fx = modal.Function.lookup(
            "sentence-encoder",
            "sentence_encoder",
            environment_name="main",
        )
        result: list[list[float]] = inf_fx.remote(sentences)
        return result
    
    except Exception as e:  # will be raised from modal if inf_fx.remote fails
        raise e
    
# if __name__ == "__main__":
#     sentences = ["the square is", "the circle is", "the triangle is"]
#     print("the square is", call_sentence_encoder(sentences))