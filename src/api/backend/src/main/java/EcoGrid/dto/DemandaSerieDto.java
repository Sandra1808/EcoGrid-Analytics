package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.Instant;

public record DemandaSerieDto(
        @JsonProperty("fecHora") Instant fecHora,
        @JsonProperty("demandaRealMWH") BigDecimal demandaRealMwh,
        @JsonProperty("demandaPredichaMWH") BigDecimal demandaPredichaMwh,
        @JsonProperty("desviacionMWH") BigDecimal desviacionMwh
) {
}