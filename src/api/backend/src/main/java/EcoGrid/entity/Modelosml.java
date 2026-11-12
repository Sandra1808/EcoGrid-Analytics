package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.ColumnDefault;
import jakarta.persistence.Convert;
import org.hibernate.type.NumericBooleanConverter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "MODELOSML")
public class Modelosml {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDMODELO", nullable = false)
    private Long id;

    @Size(max = 100)
    @NotNull
    @Column(name = "NOMBREALGORITMO", nullable = false, length = 100)
    private String nombrealgoritmo;

    @Size(max = 20)
    @NotNull
    @Column(name = "VERSION", nullable = false, length = 20)
    private String version;

    @Size(max = 255)
    @Column(name = "RUTAFICHEROARTIFACT")
    private String rutaficheroartifact;

    @Column(name = "METRICAMAE", precision = 12, scale = 4)
    private BigDecimal metricamae;

    @Column(name = "METRICARMSE", precision = 12, scale = 4)
    private BigDecimal metricarmse;

    @Column(name = "METRICAMAPE", precision = 12, scale = 4)
    private BigDecimal metricamape;

    @NotNull
    @Convert(converter = NumericBooleanConverter.class)
    @ColumnDefault("1")
    @Column(name = "INDACTIVO", nullable = false)
    private Boolean indactivo;

    @ColumnDefault("CURRENT_TIMESTAMP")
    @Column(name = "FECENTRENAMIENTO")
    private LocalDateTime fecentrenamiento;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getNombrealgoritmo() {
        return nombrealgoritmo;
    }

    public void setNombrealgoritmo(String nombrealgoritmo) {
        this.nombrealgoritmo = nombrealgoritmo;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getRutaficheroartifact() {
        return rutaficheroartifact;
    }

    public void setRutaficheroartifact(String rutaficheroartifact) {
        this.rutaficheroartifact = rutaficheroartifact;
    }

    public BigDecimal getMetricamae() {
        return metricamae;
    }

    public void setMetricamae(BigDecimal metricamae) {
        this.metricamae = metricamae;
    }

    public BigDecimal getMetricarmse() {
        return metricarmse;
    }

    public void setMetricarmse(BigDecimal metricarmse) {
        this.metricarmse = metricarmse;
    }

    public BigDecimal getMetricamape() {
        return metricamape;
    }

    public void setMetricamape(BigDecimal metricamape) {
        this.metricamape = metricamape;
    }

    public Boolean getIndactivo() {
        return indactivo;
    }

    public void setIndactivo(Boolean indactivo) {
        this.indactivo = indactivo;
    }

    public LocalDateTime getFecentrenamiento() {
        return fecentrenamiento;
    }

    public void setFecentrenamiento(LocalDateTime fecentrenamiento) {
        this.fecentrenamiento = fecentrenamiento;
    }

}