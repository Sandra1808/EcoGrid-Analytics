package EcoGrid.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Instant;

public final class UsuarioDto {
    private UsuarioDto() {
    }

    public record Response(
            Long id, String nombre, String email, String cif,
            String rol, String estado, Instant fechaAlta
    ) {
    }

    public record CreateRequest(
            @NotBlank @Size(max = 20) String cif,
            @NotBlank @Size(max = 100) String nombre,
            @NotBlank @Email @Size(max = 150) String email,
            @NotBlank @Size(min = 8, max = 100) String password,
            @NotBlank @Size(max = 50) String rol
    ) {
    }

    public record UpdateRequest(
            @NotBlank @Size(max = 100) String nombre,
            @NotBlank @Email @Size(max = 150) String email,
            @NotBlank @Size(max = 50) String rol
    ) {
    }
}