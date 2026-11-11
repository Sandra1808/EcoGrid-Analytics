package EcoGrid.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;

public record DashboardKpisDto(
        @JsonProperty("demanda_media_mw") BigDecimal demandaMediaMw,
        @JsonProperty("coste_desvio_estimado_eur") BigDecimal costeDesvioEstimadoEur,
        @JsonProperty("nivel_alerta_global") String nivelAlertaGlobal
) {
}
