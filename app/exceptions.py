class AutorNaoEncontrado(Exception):
    """O autor consultado não existe no banco."""

    def __init__(self, autor_id: int):
        super().__init__(f"Autor {autor_id} não encontrado")
        self.autor_id = autor_id


class NaoAutenticado(Exception):
    """API Key ausente ou inválida."""
