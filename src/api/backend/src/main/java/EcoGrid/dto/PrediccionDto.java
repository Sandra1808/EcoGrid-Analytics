package EcoGrid.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record PrediccionDto(
        Instant fechaHora,
        BigDecimal demandaPredichaMw,
        BigDecimal demandaBaselineMw
) {}