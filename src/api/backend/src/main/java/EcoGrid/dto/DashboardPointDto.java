package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.Instant;

public record DashboardPointDto(
        @JsonProperty("fecHora") Instant fecHora,
        @JsonProperty("demanda_mw") BigDecimal demandaMw
) {
}