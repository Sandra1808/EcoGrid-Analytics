package EcoGrid.dto;

import java.time.Instant;

public record UsuarioResponse(
        Long id,
        String nombre,
        String email,
        String cif,
        String rol,
        String estado,
        Instant fechaAlta
) {
}