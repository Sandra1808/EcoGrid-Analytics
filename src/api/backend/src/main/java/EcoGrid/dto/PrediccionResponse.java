package EcoGrid.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record PrediccionResponse(
        Instant fechaHora,
        BigDecimal demandaPredichaMw,
        BigDecimal demandaBaselineMw
) {}