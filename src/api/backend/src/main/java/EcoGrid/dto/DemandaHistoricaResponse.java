package EcoGrid.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record DemandaHistoricaResponse(
        Instant fechaHora,
        BigDecimal demandaRealMw,
        BigDecimal demandaPrevistaReeMw,
        BigDecimal demandaProgramadaMw,
        BigDecimal demandaProgramadaTotalMw
) {}