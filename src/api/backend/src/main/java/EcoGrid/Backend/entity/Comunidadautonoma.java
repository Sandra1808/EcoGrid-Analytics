package EcoGrid.Backend.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

@Entity
@Table(name = "COMUNIDADAUTONOMA")
public class Comunidadautonoma {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDCCAA", nullable = false)
    private Long id;

    @Size(max = 10)
    @NotNull
    @Column(name = "CODINE", nullable = false, length = 10)
    private String codine;

    @Size(max = 100)
    @NotNull
    @Column(name = "NOMBRECCAA", nullable = false, length = 100)
    private String nombreccaa;

    @Column(name = "LATITUDCENTROIDE", precision = 10, scale = 6)
    private BigDecimal latitudcentroide;

    @Column(name = "LONGITUDCENTROIDE", precision = 10, scale = 6)
    private BigDecimal longitudcentroide;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getCodine() {
        return codine;
    }

    public void setCodine(String codine) {
        this.codine = codine;
    }

    public String getNombreccaa() {
        return nombreccaa;
    }

    public void setNombreccaa(String nombreccaa) {
        this.nombreccaa = nombreccaa;
    }

    public BigDecimal getLatitudcentroide() {
        return latitudcentroide;
    }

    public void setLatitudcentroide(BigDecimal latitudcentroide) {
        this.latitudcentroide = latitudcentroide;
    }

    public BigDecimal getLongitudcentroide() {
        return longitudcentroide;
    }

    public void setLongitudcentroide(BigDecimal longitudcentroide) {
        this.longitudcentroide = longitudcentroide;
    }

}