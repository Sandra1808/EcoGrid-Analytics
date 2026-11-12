package EcoGrid.dto;

import java.time.Instant;
import java.time.LocalDateTime;

public record UsuarioResponse(
        Long id,
        String nombre,
        String email,
        String cif,
        String rol,
        String estado,
        LocalDateTime fechaAlta
) {
}