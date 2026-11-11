package EcoGrid.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record PrediccionLoteDto(
        @NotNull @Positive Long modeloId,
        @NotEmpty @Size(min = 24, max = 24)
        List<@NotNull @Valid Punto> predicciones
) {
    public record Punto(
            @NotNull Instant fechaHora,
            @NotNull @PositiveOrZero BigDecimal demandaPredichaMw,
            @PositiveOrZero BigDecimal demandaBaselineMw
    ) {}
}